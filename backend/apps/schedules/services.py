import zoneinfo

from django.utils import timezone as django_timezone


def get_current_on_call(schedule, at_time=None):
    """Resolve who is on call for `schedule` at `at_time` (defaults to now).

    1. A ScheduleOverride covering at_time wins outright.
    2. Otherwise, step through the rotation. Elapsed time is measured as
       *wall-clock* hours in the schedule's own timezone (not raw UTC
       delta), so rotations hand off at the same local time across DST
       transitions -- a weekly rotation anchored Monday 9am America/New_York
       still hands off Monday 9am local time even when a DST shift falls
       inside that week.
    """
    if at_time is None:
        at_time = django_timezone.now()

    override = (
        schedule.overrides.filter(start_time__lte=at_time, end_time__gt=at_time)
        .order_by("-created_at")
        .first()
    )
    if override is not None:
        return override.user

    participants = list(schedule.schedule_participants.order_by("order").select_related("user"))
    if not participants:
        return None

    tz = zoneinfo.ZoneInfo(schedule.timezone)
    at_local = at_time.astimezone(tz).replace(tzinfo=None)
    start_local = schedule.rotation_start.astimezone(tz).replace(tzinfo=None)

    elapsed_hours = (at_local - start_local).total_seconds() / 3600
    slot = int(elapsed_hours // schedule.rotation_length_hours) % len(participants)

    return participants[slot].user
