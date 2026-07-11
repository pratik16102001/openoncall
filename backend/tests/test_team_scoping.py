import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import Team, TeamMembership, User


@pytest.fixture
def two_teams(db):
    team_a = Team.objects.create(name="Team A", slug="team-a")
    team_b = Team.objects.create(name="Team B", slug="team-b")

    user_a = User.objects.create_user(email="a@example.com", password="pw12345")
    TeamMembership.objects.create(team=team_a, user=user_a, role=TeamMembership.ROLE_ADMIN)

    user_b = User.objects.create_user(email="b@example.com", password="pw12345")
    TeamMembership.objects.create(team=team_b, user=user_b, role=TeamMembership.ROLE_ADMIN)

    return team_a, team_b, user_a, user_b


def auth_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.mark.django_db
def test_login_returns_token_for_correct_credentials():
    User.objects.create_user(email="a@example.com", password="pw12345")
    resp = APIClient().post("/api/v1/auth/login/", {"email": "a@example.com", "password": "pw12345"})
    assert resp.status_code == 200
    assert "token" in resp.json()


@pytest.mark.django_db
def test_login_rejects_bad_credentials():
    User.objects.create_user(email="a@example.com", password="pw12345")
    resp = APIClient().post("/api/v1/auth/login/", {"email": "a@example.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_user_can_read_own_team(two_teams):
    team_a, _team_b, user_a, _user_b = two_teams
    resp = auth_client(user_a).get(f"/api/v1/teams/{team_a.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == team_a.id


@pytest.mark.django_db
def test_user_cannot_read_other_teams_detail(two_teams):
    _team_a, team_b, user_a, _user_b = two_teams
    resp = auth_client(user_a).get(f"/api/v1/teams/{team_b.id}/")
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_user_cannot_add_member_to_other_team(two_teams):
    _team_a, team_b, user_a, user_b = two_teams
    resp = auth_client(user_a).post(
        f"/api/v1/teams/{team_b.id}/members/", {"user": user_b.id, "role": "member"}
    )
    assert resp.status_code in (403, 404)
    assert not TeamMembership.objects.filter(team=team_b, user=user_a).exists()


@pytest.mark.django_db
def test_team_list_only_returns_own_teams(two_teams):
    team_a, team_b, user_a, _user_b = two_teams
    resp = auth_client(user_a).get("/api/v1/teams/")
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()["results"]]
    assert team_a.id in ids
    assert team_b.id not in ids


@pytest.mark.django_db
def test_unauthenticated_request_is_rejected(two_teams):
    team_a, _team_b, _user_a, _user_b = two_teams
    resp = APIClient().get(f"/api/v1/teams/{team_a.id}/")
    assert resp.status_code == 401


@pytest.mark.django_db
def test_team_admin_can_add_member_to_own_team(two_teams):
    team_a, _team_b, user_a, _user_b = two_teams
    new_user = User.objects.create_user(email="c@example.com", password="pw12345")
    resp = auth_client(user_a).post(
        f"/api/v1/teams/{team_a.id}/members/", {"user": new_user.id, "role": "member"}
    )
    assert resp.status_code == 201
    assert TeamMembership.objects.filter(team=team_a, user=new_user).exists()
