import uuid

from django.db import models

from apps.accounts.models import Team, TimeStampedModel
from apps.escalation.models import EscalationPolicy


def generate_integration_key():
    return uuid.uuid4().hex


class Service(TimeStampedModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    escalation_policy = models.ForeignKey(
        EscalationPolicy, on_delete=models.PROTECT, related_name="services"
    )
    integration_key = models.CharField(
        max_length=32, unique=True, default=generate_integration_key, editable=False
    )
    runbook_url = models.URLField(blank=True, null=True)
    runbook_markdown = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.team})"
