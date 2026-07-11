from config.celery import app as celery_app

from apps.accounts.models import Team, TeamMembership, User
from apps.incidents.models import Incident, TimelineEvent
from apps.notifications.models import NotificationAttempt
from apps.notifications.tasks import send_notification
from apps.schedules.models import Schedule
from apps.schedules.services import get_current_on_call

from .models import EscalationStep


def _resolve_step_targets(step):
    """Resolve an EscalationStep's target to a concrete list of users.

    schedule -> whoever get_current_on_call resolves for right now.
    user -> that single user.
    team -> all team members (confirmed product decision; the alternative
        considered was admins-only).
    """
    if step.target_type == EscalationStep.TARGET_USER:
        user = User.objects.filter(id=step.target_id).first()
        return [user] if user else []

    if step.target_type == EscalationStep.TARGET_SCHEDULE:
        schedule = Schedule.objects.filter(id=step.target_id).first()
        if schedule is None:
            return []
        user = get_current_on_call(schedule)
        return [user] if user else []

    if step.target_type == EscalationStep.TARGET_TEAM:
        team = Team.objects.filter(id=step.target_id).first()
        if team is None:
            return []
        return [
            membership.user
            for membership in TeamMembership.objects.filter(team=team).select_related("user")
        ]

    return []


@celery_app.task
def escalate_incident_step(incident_id, step_order, repeats_remaining=None):
    incident = (
        Incident.objects.filter(id=incident_id)
        .select_related("service__escalation_policy")
        .first()
    )
    if incident is None:
        return

    # The only mechanism that halts escalation: re-check status before
    # acting. Do not attempt to revoke the already-scheduled Celery task for
    # the next step -- that's unreliable. This no-op guard is the real
    # safety net.
    if incident.status != Incident.STATUS_TRIGGERED:
        return

    policy = incident.service.escalation_policy
    if repeats_remaining is None:
        repeats_remaining = policy.repeat_count

    step = policy.steps.filter(order=step_order).first()

    if step is None:
        if repeats_remaining > 0:
            escalate_incident_step.apply_async(
                args=[incident_id, 0],
                kwargs={"repeats_remaining": repeats_remaining - 1},
            )
            return

        TimelineEvent.objects.create(
            incident=incident,
            event_type=TimelineEvent.EVENT_ESCALATED,
            actor=None,
            message="Escalation policy exhausted without acknowledgment.",
            metadata={"step_order": step_order},
        )
        return

    users = _resolve_step_targets(step)

    incident.current_escalation_step = step_order
    incident.save(update_fields=["current_escalation_step", "updated_at"])

    for user in users:
        for channel in step.notify_channels:
            attempt = NotificationAttempt.objects.create(
                incident=incident,
                escalation_step=step_order,
                user=user,
                channel=channel,
                status=NotificationAttempt.STATUS_PENDING,
            )
            send_notification.delay(attempt.id)

    TimelineEvent.objects.create(
        incident=incident,
        event_type=(
            TimelineEvent.EVENT_NOTIFICATION_SENT
            if step_order == 0
            else TimelineEvent.EVENT_ESCALATED
        ),
        actor=None,
        message=(
            f"Escalation step {step_order} notified {len(users)} user(s) "
            f"via {', '.join(step.notify_channels) or 'no channels configured'}."
        ),
        metadata={
            "step_order": step_order,
            "target_type": step.target_type,
            "channels": step.notify_channels,
            "user_ids": [u.id for u in users],
        },
    )

    escalate_incident_step.apply_async(
        args=[incident_id, step_order + 1],
        kwargs={"repeats_remaining": repeats_remaining},
        countdown=step.timeout_minutes * 60,
    )
