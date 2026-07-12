import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team, TeamMembership, User
from apps.escalation.models import EscalationPolicy
from apps.incidents.models import Incident
from apps.services.models import Service


def auth_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.mark.django_db
def test_postmortem_reconstructs_resolved_incident_timeline():
    team = Team.objects.create(name="Platform", slug="platform")
    responder = User.objects.create_user(email="responder@example.com", password="pw12345")
    TeamMembership.objects.create(team=team, user=responder, role=TeamMembership.ROLE_ADMIN)

    policy = EscalationPolicy.objects.create(team=team, name="Default")
    service = Service.objects.create(
        team=team,
        name="checkout-api",
        escalation_policy=policy,
        runbook_url="https://runbooks.example.com/checkout-api",
        runbook_markdown="1. Check DB pool\n2. Restart workers if needed",
    )

    client = auth_client(responder)

    client.post(
        f"/webhooks/generic/{service.integration_key}/",
        {
            "external_id": "pm-1",
            "title": "High latency on checkout-api",
            "description": "p99 above threshold",
            "severity": "critical",
            "status": "firing",
        },
        format="json",
    )
    incident = Incident.objects.get()

    client.post(f"/api/v1/incidents/{incident.id}/acknowledge/")
    client.post(f"/api/v1/incidents/{incident.id}/notes/", {"message": "Found: connection pool exhausted"})
    client.post(f"/api/v1/incidents/{incident.id}/resolve/")

    # runbook is surfaced on incident detail
    detail = client.get(f"/api/v1/incidents/{incident.id}/").json()
    assert detail["runbook_url"] == "https://runbooks.example.com/checkout-api"
    assert "Check DB pool" in detail["runbook_markdown"]

    resp = client.get(f"/api/v1/incidents/{incident.id}/postmortem/")
    assert resp.status_code == 200
    markdown = resp.json()["markdown"]

    assert markdown.startswith("# Postmortem: High latency on checkout-api")
    assert "**Service:** checkout-api" in markdown
    assert "**Severity:** critical" in markdown
    assert "**Status:** resolved" in markdown
    assert "**Time to resolve:**" in markdown
    assert "## Timeline" in markdown
    assert "alert_received" in markdown.lower() or "Alert received" in markdown
    assert "acknowledged" in markdown.lower()
    assert "connection pool exhausted" in markdown
    assert "resolved" in markdown.lower()
    assert "## Runbook" in markdown
    assert "https://runbooks.example.com/checkout-api" in markdown
    assert "Restart workers if needed" in markdown

    # timeline entries appear in chronological order in the markdown text
    # (search within the Timeline section only -- the summary header above
    # it also has its own "**Acknowledged:**"/"**Resolved:**" fields)
    timeline_section = markdown[markdown.index("## Timeline") :]
    idx_received = timeline_section.find("Alert received")
    idx_ack = timeline_section.find("**Acknowledged**")
    idx_note = timeline_section.find("Note added")
    idx_resolved = timeline_section.find("**Resolved**")
    assert idx_received < idx_ack < idx_note < idx_resolved
