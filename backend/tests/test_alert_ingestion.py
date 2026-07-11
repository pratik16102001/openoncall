import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Team
from apps.alerts.models import Alert
from apps.escalation.models import EscalationPolicy
from apps.incidents.models import Incident, TimelineEvent
from apps.services.models import Service


@pytest.fixture
def service(db):
    team = Team.objects.create(name="Platform", slug="platform")
    policy = EscalationPolicy.objects.create(team=team, name="Default")
    return Service.objects.create(team=team, name="checkout-api", escalation_policy=policy)


def firing_payload(external_id="alert-123"):
    return {
        "external_id": external_id,
        "title": "High latency on checkout-api",
        "description": "p99 latency above threshold",
        "severity": "critical",
        "status": "firing",
    }


@pytest.mark.django_db
def test_generic_webhook_creates_incident_and_timeline_event(service):
    client = APIClient()
    resp = client.post(
        f"/webhooks/generic/{service.integration_key}/", firing_payload(), format="json"
    )
    assert resp.status_code == 201

    assert Alert.objects.count() == 1
    assert Incident.objects.count() == 1

    incident = Incident.objects.get()
    assert incident.status == Incident.STATUS_TRIGGERED
    assert incident.service == service

    events = TimelineEvent.objects.filter(incident=incident)
    assert events.count() == 1
    assert events.first().event_type == TimelineEvent.EVENT_ALERT_RECEIVED


@pytest.mark.django_db
def test_duplicate_external_id_does_not_create_second_incident(service):
    client = APIClient()
    payload = firing_payload("alert-dup")

    r1 = client.post(f"/webhooks/generic/{service.integration_key}/", payload, format="json")
    assert r1.status_code == 201

    r2 = client.post(f"/webhooks/generic/{service.integration_key}/", payload, format="json")
    assert r2.status_code == 200

    assert Alert.objects.count() == 1
    assert Incident.objects.count() == 1

    incident = Incident.objects.get()
    # the repeat firing should be logged, not silently dropped
    assert TimelineEvent.objects.filter(incident=incident).count() == 2


@pytest.mark.django_db
def test_resolved_payload_auto_resolves_open_incident(service):
    client = APIClient()
    payload = firing_payload("alert-resolve-me")
    client.post(f"/webhooks/generic/{service.integration_key}/", payload, format="json")

    resolved_payload = {**payload, "status": "resolved"}
    resp = client.post(f"/webhooks/generic/{service.integration_key}/", resolved_payload, format="json")
    assert resp.status_code == 200

    incident = Incident.objects.get()
    assert incident.status == Incident.STATUS_RESOLVED
    assert incident.resolved_at is not None

    resolved_events = TimelineEvent.objects.filter(
        incident=incident, event_type=TimelineEvent.EVENT_RESOLVED
    )
    assert resolved_events.count() == 1
    assert resolved_events.first().actor is None


@pytest.mark.django_db
def test_unknown_integration_key_returns_404(service):
    client = APIClient()
    resp = client.post("/webhooks/generic/does-not-exist/", firing_payload(), format="json")
    assert resp.status_code == 404
