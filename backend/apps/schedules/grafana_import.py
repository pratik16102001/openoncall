"""Imports a Grafana OnCall export into OpenOnCall Schedule/EscalationPolicy
objects for a single target Team.

There is no single canonical "export file" format for Grafana OnCall --
the spec that requested this script didn't provide one either. This
expects a JSON document shaped like a bundle of Grafana OnCall's own
public REST API responses (github.com/grafana/oncall API reference):
`users`, `schedules`, `on_call_shifts`, `escalation_chains`, and
`escalation_policies`, each a list of the corresponding API objects. A
real migration would produce this by calling those five endpoints and
concatenating the results into one file.

OpenOnCall's v1 data model is intentionally simpler than Grafana OnCall's
(a single ordered rotation per schedule, one target per escalation step),
so this import makes lossy approximations in a few places -- each one is
recorded in ImportResult.warnings rather than silently dropped:

- A Grafana schedule can layer multiple on_call_shifts; only the first is
  imported.
- A Grafana rotation slot can hold several simultaneous users
  (`rolling_users` is a list of groups); only the first user per group is
  imported.
- A Grafana escalation step can notify several people at once
  (`persons_to_notify`); OpenOnCall expands that into consecutive
  single-target steps instead.
- A Grafana step of type `notify_user_group` has no OpenOnCall equivalent
  (no user-group concept), so it's approximated as "notify the whole
  team".
- Step types other than `notify_persons`/`notify_user_group` (e.g. `wait`,
  `resolve`) have no OpenOnCall equivalent and are skipped.

Referenced Grafana users are matched to existing OpenOnCall accounts by
email. This script never creates User accounts -- provision them the
normal way first, then import.
"""

import zoneinfo
from dataclasses import dataclass, field

from django.utils import timezone as django_timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models import User
from apps.escalation.models import EscalationPolicy, EscalationStep

from .models import Schedule, ScheduleParticipant

FREQUENCY_TO_ROTATION_TYPE = {
    "daily": Schedule.ROTATION_DAILY,
    "weekly": Schedule.ROTATION_WEEKLY,
}


@dataclass
class ImportResult:
    schedules_created: list = field(default_factory=list)
    escalation_policies_created: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _resolve_user(grafana_user_id, users_by_id, warnings):
    grafana_user = users_by_id.get(grafana_user_id)
    if grafana_user is None:
        warnings.append(f"Grafana user id '{grafana_user_id}' not found in export's users list; skipped.")
        return None
    email = grafana_user.get("email")
    user = User.objects.filter(email=email).first()
    if user is None:
        warnings.append(
            f"No OpenOnCall account for '{email}' (Grafana user '{grafana_user_id}'); skipped. "
            "Create the account first, then re-run."
        )
        return None
    return user


def _import_schedule(gf_schedule, shifts_by_id, users_by_id, team, result):
    shift_ids = gf_schedule.get("on_call_shifts") or []
    if not shift_ids:
        result.warnings.append(f"Schedule '{gf_schedule.get('name')}' has no on_call_shifts; skipped.")
        return

    if len(shift_ids) > 1:
        result.warnings.append(
            f"Schedule '{gf_schedule.get('name')}' has {len(shift_ids)} layered shifts; OpenOnCall v1 "
            "supports a single rotation per schedule -- importing only the first."
        )

    shift = shifts_by_id.get(shift_ids[0])
    if shift is None:
        result.warnings.append(
            f"Schedule '{gf_schedule.get('name')}' references unknown shift '{shift_ids[0]}'; skipped."
        )
        return

    rotation_type = FREQUENCY_TO_ROTATION_TYPE.get(shift.get("frequency"), Schedule.ROTATION_CUSTOM)
    rotation_start = parse_datetime(shift["start"])
    if rotation_start is not None and django_timezone.is_naive(rotation_start):
        tz = zoneinfo.ZoneInfo(shift.get("time_zone", "UTC"))
        rotation_start = rotation_start.replace(tzinfo=tz)
    rotation_length_hours = max(1, int(shift.get("duration", 0)) // 3600)

    participant_users = []
    for group in shift.get("rolling_users") or []:
        if not group:
            continue
        if len(group) > 1:
            result.warnings.append(
                f"Shift '{shift.get('name')}' has {len(group)} simultaneous users in one rotation slot; "
                "OpenOnCall v1 schedules support one on-call user at a time -- importing only the first."
            )
        user = _resolve_user(group[0], users_by_id, result.warnings)
        if user is not None:
            participant_users.append(user)

    if not participant_users:
        result.warnings.append(f"Schedule '{gf_schedule.get('name')}' has no resolvable participants; skipped.")
        return

    schedule = Schedule.objects.create(
        team=team,
        name=gf_schedule.get("name", "Imported schedule"),
        timezone=shift.get("time_zone", "UTC"),
        rotation_type=rotation_type,
        rotation_start=rotation_start,
        rotation_length_hours=rotation_length_hours,
    )
    for order, user in enumerate(participant_users):
        ScheduleParticipant.objects.create(schedule=schedule, user=user, order=order)
    result.schedules_created.append(schedule)


def _import_escalation_chains(export_data, users_by_id, team, result):
    policies_by_chain_id = {}
    for chain in export_data.get("escalation_chains", []):
        policy = EscalationPolicy.objects.create(
            team=team, name=chain.get("name", "Imported policy"), repeat_count=0
        )
        policies_by_chain_id[chain["id"]] = policy
        result.escalation_policies_created.append(policy)

    next_order = {}
    steps = sorted(export_data.get("escalation_policies", []), key=lambda s: s.get("position", 0))
    for step in steps:
        chain_id = step.get("escalation_chain_id")
        policy = policies_by_chain_id.get(chain_id)
        if policy is None:
            result.warnings.append(f"Escalation step references unknown chain '{chain_id}'; skipped.")
            continue

        order = next_order.get(chain_id, 0)
        timeout_minutes = max(1, int(step.get("wait_delay", 300)) // 60)
        step_type = step.get("type")

        if step_type == "notify_persons":
            persons = step.get("persons_to_notify") or []
            if len(persons) > 1:
                result.warnings.append(
                    f"Policy step in chain '{chain_id}' notifies {len(persons)} people at once; OpenOnCall "
                    "v1 steps have a single target -- expanding into consecutive steps."
                )
            for person_id in persons:
                user = _resolve_user(person_id, users_by_id, result.warnings)
                if user is None:
                    continue
                EscalationStep.objects.create(
                    policy=policy,
                    order=order,
                    target_type=EscalationStep.TARGET_USER,
                    target_id=user.id,
                    timeout_minutes=timeout_minutes,
                    notify_channels=["slack"],
                )
                order += 1

        elif step_type == "notify_user_group":
            EscalationStep.objects.create(
                policy=policy,
                order=order,
                target_type=EscalationStep.TARGET_TEAM,
                target_id=team.id,
                timeout_minutes=timeout_minutes,
                notify_channels=["slack"],
            )
            result.warnings.append(
                f"Policy step in chain '{chain_id}' notifies a Grafana user group; OpenOnCall has no "
                "user-group concept -- approximated as 'notify the whole team'."
            )
            order += 1

        else:
            result.warnings.append(
                f"Policy step type '{step_type}' in chain '{chain_id}' has no OpenOnCall equivalent; skipped."
            )

        next_order[chain_id] = order


def import_grafana_oncall_export(export_data, team) -> ImportResult:
    result = ImportResult()
    users_by_id = {u["id"]: u for u in export_data.get("users", [])}
    shifts_by_id = {s["id"]: s for s in export_data.get("on_call_shifts", [])}

    for gf_schedule in export_data.get("schedules", []):
        _import_schedule(gf_schedule, shifts_by_id, users_by_id, team, result)

    _import_escalation_chains(export_data, users_by_id, team, result)

    return result
