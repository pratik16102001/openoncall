from django.db import models

from apps.accounts.models import Team, TimeStampedModel


class EscalationPolicy(TimeStampedModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="escalation_policies")
    name = models.CharField(max_length=255)
    repeat_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} ({self.team})"


class EscalationStep(TimeStampedModel):
    TARGET_SCHEDULE = "schedule"
    TARGET_USER = "user"
    TARGET_TEAM = "team"
    TARGET_TYPE_CHOICES = [
        (TARGET_SCHEDULE, "Schedule"),
        (TARGET_USER, "User"),
        (TARGET_TEAM, "Team"),
    ]

    CHANNEL_CHOICES = [
        ("slack", "Slack"),
        ("sms", "SMS"),
        ("voice", "Voice"),
        ("push", "Web Push"),
    ]

    policy = models.ForeignKey(EscalationPolicy, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    target_type = models.CharField(max_length=16, choices=TARGET_TYPE_CHOICES)
    target_id = models.PositiveIntegerField()
    timeout_minutes = models.PositiveIntegerField()
    notify_channels = models.JSONField(default=list)

    class Meta:
        ordering = ["order"]
        unique_together = ("policy", "order")

    def __str__(self):
        return f"Step {self.order} of {self.policy}"
