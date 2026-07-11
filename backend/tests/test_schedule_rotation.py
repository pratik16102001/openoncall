import datetime
import zoneinfo

import pytest

from apps.accounts.models import Team, User
from apps.schedules.models import Schedule, ScheduleOverride, ScheduleParticipant
from apps.schedules.services import get_current_on_call


@pytest.fixture
def weekly_schedule(db):
    team = Team.objects.create(name="Platform", slug="platform")
    alice = User.objects.create_user(email="alice@example.com", password="pw12345")
    bob = User.objects.create_user(email="bob@example.com", password="pw12345")
    carol = User.objects.create_user(email="carol@example.com", password="pw12345")

    ny_tz = zoneinfo.ZoneInfo("America/New_York")
    rotation_start = datetime.datetime(2026, 1, 5, 9, 0, tzinfo=ny_tz)  # a Monday 9am ET

    schedule = Schedule.objects.create(
        team=team,
        name="Primary",
        timezone="America/New_York",
        rotation_type=Schedule.ROTATION_WEEKLY,
        rotation_start=rotation_start,
        rotation_length_hours=168,
    )
    for i, user in enumerate([alice, bob, carol]):
        ScheduleParticipant.objects.create(schedule=schedule, user=user, order=i)

    return schedule, alice, bob, carol


def ny(*args):
    return datetime.datetime(*args, tzinfo=zoneinfo.ZoneInfo("America/New_York"))


@pytest.mark.django_db
def test_first_slot_is_on_call_at_rotation_start(weekly_schedule):
    schedule, alice, _bob, _carol = weekly_schedule
    assert get_current_on_call(schedule, ny(2026, 1, 5, 9, 0)) == alice


@pytest.mark.django_db
def test_second_participant_on_call_one_week_in(weekly_schedule):
    schedule, _alice, bob, _carol = weekly_schedule
    assert get_current_on_call(schedule, ny(2026, 1, 12, 9, 0)) == bob


@pytest.mark.django_db
def test_rotation_wraps_around(weekly_schedule):
    schedule, alice, _bob, _carol = weekly_schedule
    # 3 participants -> week 3 (index 3 % 3 == 0) is alice again
    assert get_current_on_call(schedule, ny(2026, 1, 26, 9, 0)) == alice


@pytest.mark.django_db
def test_override_takes_precedence_over_rotation(weekly_schedule):
    schedule, alice, _bob, carol = weekly_schedule
    ScheduleOverride.objects.create(
        schedule=schedule,
        user=carol,
        start_time=ny(2026, 1, 5, 12, 0),
        end_time=ny(2026, 1, 5, 18, 0),
        reason="Alice is out sick",
    )
    # inside the override window -> carol, even though alice's rotation slot is active
    assert get_current_on_call(schedule, ny(2026, 1, 5, 14, 0)) == carol
    # outside the override window -> back to the rotation
    assert get_current_on_call(schedule, ny(2026, 1, 5, 19, 0)) == alice


@pytest.mark.django_db
def test_rotation_hands_off_at_local_time_across_dst_transition(weekly_schedule):
    """DST in the US in 2026 ends Nov 1. A rotation anchored at 9am ET on a
    Monday before the transition should still hand off at 9am ET (local
    wall-clock time) on the following Monday, not 9am UTC-equivalent."""
    schedule, alice, bob, _carol = weekly_schedule
    schedule.rotation_start = ny(2026, 10, 26, 9, 0)  # Monday before DST ends
    schedule.save(update_fields=["rotation_start"])

    just_before_handoff = ny(2026, 11, 2, 8, 59)
    just_after_handoff = ny(2026, 11, 2, 9, 1)

    assert get_current_on_call(schedule, just_before_handoff) == alice
    assert get_current_on_call(schedule, just_after_handoff) == bob


@pytest.mark.django_db
def test_no_participants_returns_none(db):
    team = Team.objects.create(name="Empty", slug="empty")
    schedule = Schedule.objects.create(
        team=team,
        name="Empty",
        timezone="UTC",
        rotation_type=Schedule.ROTATION_WEEKLY,
        rotation_start=ny(2026, 1, 5, 9, 0),
        rotation_length_hours=168,
    )
    assert get_current_on_call(schedule, ny(2026, 1, 5, 9, 0)) is None
