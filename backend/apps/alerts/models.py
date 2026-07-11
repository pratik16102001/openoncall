from django.db import models

from apps.accounts.models import TimeStampedModel
from apps.services.models import Service


class Alert(TimeStampedModel):
    SOURCE_ALERTMANAGER = "alertmanager"
    SOURCE_DATADOG = "datadog"
    SOURCE_CLOUDWATCH = "cloudwatch"
    SOURCE_SENTRY = "sentry"
    SOURCE_GENERIC = "generic"
    SOURCE_CHOICES = [
        (SOURCE_ALERTMANAGER, "Alertmanager"),
        (SOURCE_DATADOG, "Datadog"),
        (SOURCE_CLOUDWATCH, "CloudWatch"),
        (SOURCE_SENTRY, "Sentry"),
        (SOURCE_GENERIC, "Generic"),
    ]

    SEVERITY_CRITICAL = "critical"
    SEVERITY_WARNING = "warning"
    SEVERITY_INFO = "info"
    SEVERITY_CHOICES = [
        (SEVERITY_CRITICAL, "Critical"),
        (SEVERITY_WARNING, "Warning"),
        (SEVERITY_INFO, "Info"),
    ]

    STATUS_FIRING = "firing"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_FIRING, "Firing"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="alerts")
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    external_id = models.CharField(max_length=512)
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES)
    raw_payload = models.JSONField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    received_at = models.DateTimeField()

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "source", "external_id"], name="uniq_alert_dedup_key"
            )
        ]

    def get_team(self):
        return self.service.team

    def __str__(self):
        return f"{self.title} [{self.source}:{self.external_id}]"
