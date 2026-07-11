from django.conf import settings
from django.db import models

from apps.accounts.models import TimeStampedModel
from apps.incidents.models import Incident


class NotificationAttempt(TimeStampedModel):
    CHANNEL_SLACK = "slack"
    CHANNEL_SMS = "sms"
    CHANNEL_VOICE = "voice"
    CHANNEL_PUSH = "push"
    CHANNEL_CHOICES = [
        (CHANNEL_SLACK, "Slack"),
        (CHANNEL_SMS, "SMS"),
        (CHANNEL_VOICE, "Voice"),
        (CHANNEL_PUSH, "Web Push"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_FAILED, "Failed"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
    ]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="notification_attempts")
    escalation_step = models.PositiveIntegerField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    channel = models.CharField(max_length=16, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    provider_message_id = models.CharField(max_length=255, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    def get_team(self):
        return self.incident.service.team

    def __str__(self):
        return f"{self.channel} to {self.user} for incident #{self.incident_id} ({self.status})"
