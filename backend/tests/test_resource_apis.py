import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team, TeamMembership, User
from apps.escalation.models import EscalationPolicy
from apps.schedules.models import Schedule
from apps.services.models import Service


def auth_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def team_and_users(db):
    team = Team.objects.create(name="Platform", slug="platform")
    alice = User.objects.create_user(email="alice@example.com", password="pw12345")
    bob = User.objects.create_user(email="bob@example.com", password="pw12345")
    TeamMembership.objects.create(team=team, user=alice, role=TeamMembership.ROLE_ADMIN)
    TeamMembership.objects.create(team=team, user=bob, role=TeamMembership.ROLE_MEMBER)

    other_team = Team.objects.create(name="Other", slug="other")
    outsider = User.objects.create_user(email="outsider@example.com", password="pw12345")
    TeamMembership.objects.create(team=other_team, user=outsider, role=TeamMembership.ROLE_ADMIN)

    return team, alice, bob, other_team, outsider


# --- Schedules -----------------------------------------------------------------


@pytest.mark.django_db
def test_create_schedule_with_participants(team_and_users):
    team, alice, bob, _other_team, _outsider = team_and_users
    client = auth_client(alice)

    resp = client.post(
        "/api/v1/schedules/",
        {
            "team": team.id,
            "name": "Primary",
            "timezone": "America/New_York",
            "rotation_type": "weekly",
            "rotation_start": "2026-01-05T09:00:00Z",
            "rotation_length_hours": 168,
            "participants": [
                {"user": alice.id, "order": 0},
                {"user": bob.id, "order": 1},
            ],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.json()
    schedule = Schedule.objects.get()
    assert schedule.schedule_participants.count() == 2


@pytest.mark.django_db
def test_cannot_create_schedule_for_another_team(team_and_users):
    _team, _alice, _bob, other_team, _outsider = team_and_users
    outsider2 = User.objects.create_user(email="outsider2@example.com", password="pw12345")
    TeamMembership.objects.create(team=other_team, user=outsider2, role=TeamMembership.ROLE_MEMBER)
    # alice is not a member of other_team
    team, alice, _bob, _other_team, _outsider = team_and_users
    client = auth_client(alice)

    resp = client.post(
        "/api/v1/schedules/",
        {
            "team": other_team.id,
            "name": "Sneaky",
            "timezone": "UTC",
            "rotation_type": "weekly",
            "rotation_start": "2026-01-05T09:00:00Z",
            "rotation_length_hours": 168,
        },
        format="json",
    )
    assert resp.status_code == 403
    assert not Schedule.objects.filter(team=other_team, name="Sneaky").exists()


@pytest.mark.django_db
def test_on_call_endpoint_returns_current_user(team_and_users):
    team, alice, bob, _other_team, _outsider = team_and_users
    schedule = Schedule.objects.create(
        team=team,
        name="Primary",
        timezone="UTC",
        rotation_type=Schedule.ROTATION_WEEKLY,
        rotation_start="2026-01-05T09:00:00Z",
        rotation_length_hours=168,
    )
    from apps.schedules.models import ScheduleParticipant

    ScheduleParticipant.objects.create(schedule=schedule, user=alice, order=0)
    ScheduleParticipant.objects.create(schedule=schedule, user=bob, order=1)

    client = auth_client(alice)
    resp = client.get(f"/api/v1/schedules/{schedule.id}/on-call/", {"at": "2026-01-05T09:00:00Z"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == alice.email

    resp = client.get(f"/api/v1/schedules/{schedule.id}/on-call/", {"at": "2026-01-12T09:00:00Z"})
    assert resp.json()["user"]["email"] == bob.email


@pytest.mark.django_db
def test_create_override_via_api(team_and_users):
    team, alice, bob, _other_team, _outsider = team_and_users
    schedule = Schedule.objects.create(
        team=team,
        name="Primary",
        timezone="UTC",
        rotation_type=Schedule.ROTATION_WEEKLY,
        rotation_start="2026-01-05T09:00:00Z",
        rotation_length_hours=168,
    )
    client = auth_client(alice)
    resp = client.post(
        f"/api/v1/schedules/{schedule.id}/overrides/",
        {
            "user": bob.id,
            "start_time": "2026-01-06T00:00:00Z",
            "end_time": "2026-01-06T12:00:00Z",
            "reason": "Alice is travelling",
        },
        format="json",
    )
    assert resp.status_code == 201
    assert schedule.overrides.count() == 1


# --- Escalation Policies --------------------------------------------------------


@pytest.mark.django_db
def test_create_escalation_policy_with_nested_steps(team_and_users):
    team, alice, bob, _other_team, _outsider = team_and_users
    client = auth_client(alice)

    resp = client.post(
        "/api/v1/escalation-policies/",
        {
            "team": team.id,
            "name": "Default",
            "repeat_count": 1,
            "steps": [
                {
                    "order": 0,
                    "target_type": "user",
                    "target_id": alice.id,
                    "timeout_minutes": 5,
                    "notify_channels": ["slack"],
                },
                {
                    "order": 1,
                    "target_type": "user",
                    "target_id": bob.id,
                    "timeout_minutes": 10,
                    "notify_channels": ["sms"],
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 201, resp.json()
    policy = EscalationPolicy.objects.get()
    assert policy.steps.count() == 2


# --- Services --------------------------------------------------------------------


@pytest.mark.django_db
def test_create_service_returns_integration_key_and_webhook_urls(team_and_users):
    team, alice, _bob, _other_team, _outsider = team_and_users
    policy = EscalationPolicy.objects.create(team=team, name="Default")
    client = auth_client(alice)

    resp = client.post(
        "/api/v1/services/",
        {"team": team.id, "name": "checkout-api", "escalation_policy": policy.id},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["integration_key"]
    assert data["webhook_urls"]["generic"].endswith(f"/webhooks/generic/{data['integration_key']}/")


@pytest.mark.django_db
def test_regenerate_key_changes_integration_key(team_and_users):
    team, alice, _bob, _other_team, _outsider = team_and_users
    policy = EscalationPolicy.objects.create(team=team, name="Default")
    service = Service.objects.create(team=team, name="checkout-api", escalation_policy=policy)
    old_key = service.integration_key

    client = auth_client(alice)
    resp = client.post(f"/api/v1/services/{service.id}/regenerate-key/")
    assert resp.status_code == 200
    service.refresh_from_db()
    assert service.integration_key != old_key


@pytest.mark.django_db
def test_outsider_cannot_see_or_modify_team_resources(team_and_users):
    team, alice, _bob, _other_team, outsider = team_and_users
    policy = EscalationPolicy.objects.create(team=team, name="Default")
    service = Service.objects.create(team=team, name="checkout-api", escalation_policy=policy)

    client = auth_client(outsider)
    resp = client.get(f"/api/v1/services/{service.id}/")
    assert resp.status_code == 404
    resp = client.post(f"/api/v1/services/{service.id}/regenerate-key/")
    assert resp.status_code == 404
