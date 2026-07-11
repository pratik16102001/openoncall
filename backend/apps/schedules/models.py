from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel, Team


class Schedule(TimeStampedModel):
    ROTATION_DAILY = "daily"
    ROTATION_WEEKLY = "weekly"
    ROTATION_CUSTOM = "custom"
    ROTATION_TYPE_CHOICES = [
        (ROTATION_DAILY, "Daily"),
        (ROTATION_WEEKLY, "Weekly"),
        (ROTATION_CUSTOM, "Custom"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="schedules")
    name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=64)
    rotation_type = models.CharField(max_length=16, choices=ROTATION_TYPE_CHOICES)
    rotation_start = models.DateTimeField()
    rotation_length_hours = models.PositiveIntegerField()
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ScheduleParticipant",
        related_name="schedules",
    )

    def __str__(self):
        return f"{self.name} ({self.team})"


class ScheduleParticipant(TimeStampedModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="schedule_participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = ("schedule", "order")

    def __str__(self):
        return f"{self.user} (#{self.order}) on {self.schedule}"


class ScheduleOverride(TimeStampedModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="overrides")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user} covers {self.schedule} {self.start_time}–{self.end_time}"
