from django.utils import timezone

from .models import Incident, TimelineEvent


def acknowledge_incident(incident, actor=None):
    """Acknowledge an incident, halting escalation (Section 6.2's status
    re-check is what actually stops the chain; this just flips the status
    it checks). Idempotent: acknowledging an already-acted-on incident is a
    no-op so both the Slack button and the REST endpoint can call this
    safely without racing each other.
    """
    if incident.status != Incident.STATUS_TRIGGERED:
        return incident

    incident.status = Incident.STATUS_ACKNOWLEDGED
    incident.acknowledged_at = timezone.now()
    incident.assigned_to = actor
    incident.save(update_fields=["status", "acknowledged_at", "assigned_to", "updated_at"])

    TimelineEvent.objects.create(
        incident=incident,
        event_type=TimelineEvent.EVENT_ACKNOWLEDGED,
        actor=actor,
        message=f"Acknowledged by {actor}." if actor else "Acknowledged.",
    )
    return incident


def resolve_incident(incident, actor=None):
    """Resolve an incident. Allowed from any non-resolved status -- an
    incident can be resolved without ever being acknowledged (e.g. the
    underlying condition self-healed), same as the auto-resolve path in
    alerts.services.ingest_alert. Idempotent for the same reason as
    acknowledge_incident.
    """
    if incident.status == Incident.STATUS_RESOLVED:
        return incident

    incident.status = Incident.STATUS_RESOLVED
    incident.resolved_at = timezone.now()
    incident.save(update_fields=["status", "resolved_at", "updated_at"])

    TimelineEvent.objects.create(
        incident=incident,
        event_type=TimelineEvent.EVENT_RESOLVED,
        actor=actor,
        message=f"Resolved by {actor}." if actor else "Resolved.",
    )
    return incident


def add_note(incident, actor, message):
    return TimelineEvent.objects.create(
        incident=incident,
        event_type=TimelineEvent.EVENT_NOTE_ADDED,
        actor=actor,
        message=message,
    )
