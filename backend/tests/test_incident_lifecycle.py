import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team, TeamMembership, User
from apps.escalation.models import EscalationPolicy, EscalationStep
from apps.escalation.tasks import escalate_incident_step
from apps.incidents.models import Incident, TimelineEvent
from apps.notifications.models import NotificationAttempt
from apps.services.models import Service


def auth_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def team_setup(db):
    team = Team.objects.create(name="Platform", slug="platform")
    responder = User.objects.create_user(email="responder@example.com", password="pw12345")
    TeamMembership.objects.create(team=team, user=responder, role=TeamMembership.ROLE_ADMIN)

    policy = EscalationPolicy.objects.create(team=team, name="Default", repeat_count=0)
    EscalationStep.objects.create(
        policy=policy,
        order=0,
        target_type=EscalationStep.TARGET_USER,
        target_id=responder.id,
        timeout_minutes=5,
        notify_channels=["slack"],
    )
    service = Service.objects.create(team=team, name="checkout-api", escalation_policy=policy)
    return team, responder, service


@pytest.mark.django_db
def test_full_incident_lifecycle_via_api(team_setup):
    team, responder, service = team_setup
    client = auth_client(responder)

    # 1. alert in -> incident created
    payload = {
        "external_id": "alert-lifecycle-1",
        "title": "High latency on checkout-api",
        "description": "p99 above threshold",
        "severity": "critical",
        "status": "firing",
    }
    resp = client.post(f"/webhooks/generic/{service.integration_key}/", payload, format="json")
    assert resp.status_code == 201

    incident = Incident.objects.get()
    assert incident.status == Incident.STATUS_TRIGGERED

    # 2. escalates once (simulating the scheduled Celery hop firing)
    escalate_incident_step(incident.id, 0)
    incident.refresh_from_db()
    assert incident.current_escalation_step == 0
    assert NotificationAttempt.objects.filter(incident=incident).count() == 1

    # 3. acknowledged via API
    resp = client.post(f"/api/v1/incidents/{incident.id}/acknowledge/")
    assert resp.status_code == 200
    incident.refresh_from_db()
    assert incident.status == Incident.STATUS_ACKNOWLEDGED
    assert incident.assigned_to == responder
    assert incident.acknowledged_at is not None

    # 4. escalation confirmed to stop: simulate the next scheduled hop
    # firing anyway -- the status re-check must make it a no-op.
    escalate_incident_step(incident.id, 1)
    assert NotificationAttempt.objects.filter(incident=incident).count() == 1  # unchanged

    # a manual note, while we're at it
    resp = client.post(f"/api/v1/incidents/{incident.id}/notes/", {"message": "Investigating DB pool exhaustion"})
    assert resp.status_code == 201

    # 5. resolved via API
    resp = client.post(f"/api/v1/incidents/{incident.id}/resolve/")
    assert resp.status_code == 200
    incident.refresh_from_db()
    assert incident.status == Incident.STATUS_RESOLVED
    assert incident.resolved_at is not None

    # 6. timeline shows the complete correct sequence
    resp = client.get(f"/api/v1/incidents/{incident.id}/")
    assert resp.status_code == 200
    timeline = resp.json()["timeline"]
    assert [e["event_type"] for e in timeline] == [
        TimelineEvent.EVENT_ALERT_RECEIVED,
        TimelineEvent.EVENT_NOTIFICATION_SENT,
        TimelineEvent.EVENT_ACKNOWLEDGED,
        TimelineEvent.EVENT_NOTE_ADDED,
        TimelineEvent.EVENT_RESOLVED,
    ]
    assert timeline[2]["actor"] == responder.id
    assert timeline[4]["actor"] == responder.id


@pytest.mark.django_db
def test_incidents_list_filters_by_status_service_team(team_setup):
    team, responder, service = team_setup
    client = auth_client(responder)

    for i in range(2):
        client.post(
            f"/webhooks/generic/{service.integration_key}/",
            {
                "external_id": f"alert-{i}",
                "title": f"Incident {i}",
                "severity": "warning",
                "status": "firing",
            },
            format="json",
        )
    incident = Incident.objects.first()
    client.post(f"/api/v1/incidents/{incident.id}/resolve/")

    resp = client.get("/api/v1/incidents/", {"status": "resolved"})
    assert resp.json()["count"] == 1

    resp = client.get("/api/v1/incidents/", {"service": service.id})
    assert resp.json()["count"] == 2

    resp = client.get("/api/v1/incidents/", {"team": team.id})
    assert resp.json()["count"] == 2


@pytest.mark.django_db
def test_user_from_other_team_cannot_act_on_incident(team_setup):
    _team, _responder, service = team_setup
    other_team = Team.objects.create(name="Other", slug="other")
    outsider = User.objects.create_user(email="outsider@example.com", password="pw12345")
    TeamMembership.objects.create(team=other_team, user=outsider, role=TeamMembership.ROLE_ADMIN)

    resp = APIClient().post(
        f"/webhooks/generic/{service.integration_key}/",
        {"external_id": "a1", "title": "t", "severity": "info", "status": "firing"},
        format="json",
    )
    assert resp.status_code == 201
    incident = Incident.objects.get()

    client = auth_client(outsider)
    resp = client.post(f"/api/v1/incidents/{incident.id}/acknowledge/")
    assert resp.status_code in (403, 404)

    incident.refresh_from_db()
    assert incident.status == Incident.STATUS_TRIGGERED
