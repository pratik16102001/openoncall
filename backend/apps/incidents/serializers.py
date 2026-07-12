from rest_framework import serializers

from .models import Incident, TimelineEvent


class TimelineEventSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = TimelineEvent
        fields = ["id", "event_type", "actor", "actor_email", "message", "metadata", "created_at"]
        read_only_fields = fields


class IncidentSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    team = serializers.IntegerField(source="service.team_id", read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "title",
            "status",
            "service",
            "service_name",
            "team",
            "triggering_alert",
            "current_escalation_step",
            "assigned_to",
            "acknowledged_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class IncidentDetailSerializer(IncidentSerializer):
    timeline = TimelineEventSerializer(source="timeline_events", many=True, read_only=True)
    runbook_url = serializers.URLField(source="service.runbook_url", read_only=True, default=None)
    runbook_markdown = serializers.CharField(
        source="service.runbook_markdown", read_only=True, default=None
    )

    class Meta(IncidentSerializer.Meta):
        fields = IncidentSerializer.Meta.fields + ["timeline", "runbook_url", "runbook_markdown"]


class NoteSerializer(serializers.Serializer):
    message = serializers.CharField()
