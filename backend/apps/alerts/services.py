from django.utils import timezone

from apps.escalation.tasks import escalate_incident_step
from apps.incidents.models import Incident, TimelineEvent

from .models import Alert


def _open_incident_for(alert):
    return Incident.objects.filter(triggering_alert=alert).exclude(status=Incident.STATUS_RESOLVED).first()


def ingest_alert(service, source, normalized, raw_payload):
    """Implements Section 6.1 steps 4-6: dedup, incident creation, auto-resolve.

    Returns (alert, incident_or_None, created_new_incident: bool).
    """
    external_id = normalized["external_id"]
    incoming_status = normalized["status"]
    now = timezone.now()

    existing = Alert.objects.filter(service=service, source=source, external_id=external_id).first()

    # --- resolved payload -------------------------------------------------
    if incoming_status == Alert.STATUS_RESOLVED:
        if existing is None:
            # Nothing to resolve; still record the alert for visibility/audit.
            alert = Alert.objects.create(
                service=service,
                source=source,
                external_id=external_id,
                title=normalized["title"],
                description=normalized.get("description", ""),
                severity=normalized["severity"],
                raw_payload=raw_payload,
                status=Alert.STATUS_RESOLVED,
                received_at=now,
            )
            return alert, None, False

        incident = _open_incident_for(existing)
        existing.status = Alert.STATUS_RESOLVED
        existing.save(update_fields=["status", "updated_at"])
        if incident is not None:
            incident.status = Incident.STATUS_RESOLVED
            incident.resolved_at = now
            incident.save(update_fields=["status", "resolved_at", "updated_at"])
            TimelineEvent.objects.create(
                incident=incident,
                event_type=TimelineEvent.EVENT_RESOLVED,
                actor=None,
                message="Monitoring source reported this alert as resolved.",
                metadata={"source": source, "external_id": external_id},
            )
        return existing, incident, False

    # --- firing payload -----------------------------------------------------
    if existing is not None and existing.status == Alert.STATUS_FIRING:
        # Duplicate/repeat notification from the monitoring source.
        incident = _open_incident_for(existing)
        if incident is not None:
            TimelineEvent.objects.create(
                incident=incident,
                event_type=TimelineEvent.EVENT_ALERT_RECEIVED,
                actor=None,
                message="Duplicate firing notification received from monitoring source.",
                metadata={"source": source, "external_id": external_id},
            )
        return existing, incident, False

    if existing is not None:
        # Existing alert had resolved and is now firing again -- refresh it
        # in place (the dedup key is permanent) rather than violating the
        # unique constraint with a new row.
        existing.title = normalized["title"]
        existing.description = normalized.get("description", "")
        existing.severity = normalized["severity"]
        existing.raw_payload = raw_payload
        existing.status = Alert.STATUS_FIRING
        existing.received_at = now
        existing.save()
        alert = existing
    else:
        alert = Alert.objects.create(
            service=service,
            source=source,
            external_id=external_id,
            title=normalized["title"],
            description=normalized.get("description", ""),
            severity=normalized["severity"],
            raw_payload=raw_payload,
            status=Alert.STATUS_FIRING,
            received_at=now,
        )

    incident = Incident.objects.create(
        service=service,
        triggering_alert=alert,
        title=alert.title,
        status=Incident.STATUS_TRIGGERED,
    )
    TimelineEvent.objects.create(
        incident=incident,
        event_type=TimelineEvent.EVENT_ALERT_RECEIVED,
        actor=None,
        message=f"Alert received from {source}.",
        metadata={"source": source, "external_id": external_id, "severity": alert.severity},
    )
    escalate_incident_step.delay(incident.id, 0)
    return alert, incident, True
