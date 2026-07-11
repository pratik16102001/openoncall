from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel
from apps.alerts.models import Alert
from apps.services.models import Service


class Incident(TimeStampedModel):
    STATUS_TRIGGERED = "triggered"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_TRIGGERED, "Triggered"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="incidents")
    triggering_alert = models.ForeignKey(Alert, on_delete=models.PROTECT, related_name="incidents")
    title = models.CharField(max_length=512)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_TRIGGERED)
    current_escalation_step = models.PositiveIntegerField(default=0)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_incidents",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def get_team(self):
        return self.service.team

    def __str__(self):
        return f"Incident #{self.pk}: {self.title}"


class TimelineEvent(TimeStampedModel):
    EVENT_ALERT_RECEIVED = "alert_received"
    EVENT_NOTIFICATION_SENT = "notification_sent"
    EVENT_ESCALATED = "escalated"
    EVENT_ACKNOWLEDGED = "acknowledged"
    EVENT_RESOLVED = "resolved"
    EVENT_NOTE_ADDED = "note_added"
    EVENT_TYPE_CHOICES = [
        (EVENT_ALERT_RECEIVED, "Alert received"),
        (EVENT_NOTIFICATION_SENT, "Notification sent"),
        (EVENT_ESCALATED, "Escalated"),
        (EVENT_ACKNOWLEDGED, "Acknowledged"),
        (EVENT_RESOLVED, "Resolved"),
        (EVENT_NOTE_ADDED, "Note added"),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="timeline_events")
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    message = models.TextField()
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def get_team(self):
        return self.incident.service.team

    def __str__(self):
        return f"{self.event_type} on incident #{self.incident_id}"
