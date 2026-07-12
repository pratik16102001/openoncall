import json
from pathlib import Path

import pytest

from apps.accounts.models import Team, User
from apps.escalation.models import EscalationStep
from apps.schedules.grafana_import import import_grafana_oncall_export
from apps.schedules.models import Schedule

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "grafana_oncall_export_sample.json"


@pytest.fixture
def export_data():
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture
def team_with_matching_users(db):
    team = Team.objects.create(name="Platform", slug="platform")
    alice = User.objects.create_user(email="alice@example.com", password="pw12345")
    bob = User.objects.create_user(email="bob@example.com", password="pw12345")
    carol = User.objects.create_user(email="carol@example.com", password="pw12345")
    # Deliberately NOT creating an account for ghost@example.com, to exercise
    # the "no matching OpenOnCall account" warning path.
    return team, alice, bob, carol


@pytest.mark.django_db
def test_import_creates_schedule_with_ordered_participants(export_data, team_with_matching_users):
    team, alice, bob, carol = team_with_matching_users

    result = import_grafana_oncall_export(export_data, team)

    assert len(result.schedules_created) == 1
    schedule = Schedule.objects.get()
    assert schedule.name == "Primary On-Call"
    assert schedule.team == team
    assert schedule.rotation_type == Schedule.ROTATION_WEEKLY
    assert schedule.rotation_length_hours == 168
    assert schedule.timezone == "America/New_York"

    participants = list(schedule.schedule_participants.order_by("order"))
    assert [p.user for p in participants] == [alice, bob, carol]
    assert [p.order for p in participants] == [0, 1, 2]


@pytest.mark.django_db
def test_import_creates_escalation_policy_with_expanded_and_approximated_steps(
    export_data, team_with_matching_users
):
    team, alice, bob, carol = team_with_matching_users

    result = import_grafana_oncall_export(export_data, team)

    assert len(result.escalation_policies_created) == 1
    policy = result.escalation_policies_created[0]
    assert policy.name == "Default Escalation Chain"

    steps = list(policy.steps.order_by("order"))
    assert len(steps) == 4  # EP1(1) + EP2 expanded(2) + EP3(1); EP4/EP5 contribute none

    assert steps[0].target_type == EscalationStep.TARGET_USER
    assert steps[0].target_id == alice.id
    assert steps[0].timeout_minutes == 5

    # EP2 notified bob and carol simultaneously -- expanded into consecutive steps
    assert steps[1].target_type == EscalationStep.TARGET_USER
    assert steps[1].target_id == bob.id
    assert steps[1].timeout_minutes == 10
    assert steps[2].target_type == EscalationStep.TARGET_USER
    assert steps[2].target_id == carol.id
    assert steps[2].timeout_minutes == 10

    # EP3 (notify_user_group) approximated as "notify the whole team"
    assert steps[3].target_type == EscalationStep.TARGET_TEAM
    assert steps[3].target_id == team.id


@pytest.mark.django_db
def test_import_warns_about_lossy_and_unresolvable_cases(export_data, team_with_matching_users):
    team, _alice, _bob, _carol = team_with_matching_users

    result = import_grafana_oncall_export(export_data, team)
    warnings_text = "\n".join(result.warnings)

    assert "notifies 2 people at once" in warnings_text  # EP2 expansion
    assert "user group" in warnings_text  # EP3 approximation
    assert "resolve" in warnings_text and "no OpenOnCall equivalent" in warnings_text  # EP4
    assert "ghost@example.com" in warnings_text  # EP5: known Grafana user, no OpenOnCall account
    assert "U_DOES_NOT_EXIST" in warnings_text  # EP5: unknown Grafana user entirely
    # EP2 and EP5 each notify 2 people at once (2 warnings), EP3's team
    # approximation, EP4's unsupported type, and EP5's two unresolvable
    # persons (ghost@example.com has no account, U_DOES_NOT_EXIST isn't in
    # the export at all) = 6 total.
    assert len(result.warnings) == 6


@pytest.mark.django_db
def test_import_management_command(export_data, team_with_matching_users, tmp_path):
    from django.core.management import call_command

    team, _alice, _bob, _carol = team_with_matching_users
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(export_data))

    call_command("import_grafana_oncall", str(export_path), team=team.slug)

    assert Schedule.objects.filter(team=team).count() == 1
