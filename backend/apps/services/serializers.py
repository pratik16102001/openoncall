from rest_framework import serializers

from .models import Service

WEBHOOK_SOURCES = ["alertmanager", "datadog", "cloudwatch", "sentry", "generic"]


class ServiceSerializer(serializers.ModelSerializer):
    webhook_urls = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "team",
            "name",
            "escalation_policy",
            "integration_key",
            "webhook_urls",
            "runbook_url",
            "runbook_markdown",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "integration_key", "webhook_urls", "created_at", "updated_at"]

    def get_webhook_urls(self, obj):
        request = self.context.get("request")
        base = request.build_absolute_uri("/webhooks/") if request else "/webhooks/"
        return {source: f"{base}{source}/{obj.integration_key}/" for source in WEBHOOK_SOURCES}
