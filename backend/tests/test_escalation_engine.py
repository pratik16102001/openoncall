import pytest
from django.utils import timezone

from apps.accounts.models import Team, User
from apps.alerts.models import Alert
from apps.escalation.models import EscalationPolicy, EscalationStep
from apps.escalation.tasks import escalate_incident_step
from apps.incidents.models import Incident, TimelineEvent
from apps.notifications.models import NotificationAttempt
from apps.services.models import Service


@pytest.fixture
def synchronous_escalation_chain(monkeypatch):
    """Collapse the countdown-based escalation chain into synchronous calls.

    escalate_incident_step schedules its own next hop via
    `apply_async(..., countdown=...)`. Rather than fighting Celery's eager
    mode (which has a known quirk where a task recursively calling its own
    apply_async from within its own execution can't find itself in the task
    registry), we simulate "time passing" by making that recursive call
    invoke the task function directly and synchronously. This is the
    "simulated time" the Phase 4 DoD asks for: no real sleeping, no Celery
    broker involved for the recursive hops, full observability in-process.
    """

    def run_immediately(args=None, kwargs=None, countdown=None, **_ignored):
        return escalate_incident_step(*(args or []), **(kwargs or {}))

    monkeypatch.setattr(escalate_incident_step, "apply_async", run_immediately)


@pytest.fixture
def incident_with_two_step_policy(db):
    team = Team.objects.create(name="Platform", slug="platform")
    user1 = User.objects.create_user(email="u1@example.com", password="pw12345")
    user2 = User.objects.create_user(email="u2@example.com", password="pw12345")

    policy = EscalationPolicy.objects.create(team=team, name="Default", repeat_count=0)
    EscalationStep.objects.create(
        policy=policy,
        order=0,
        target_type=EscalationStep.TARGET_USER,
        target_id=user1.id,
        timeout_minutes=5,
        notify_channels=["slack"],
    )
    EscalationStep.objects.create(
        policy=policy,
        order=1,
        target_type=EscalationStep.TARGET_USER,
        target_id=user2.id,
        timeout_minutes=5,
        notify_channels=["slack", "sms"],
    )

    service = Service.objects.create(team=team, name="checkout-api", escalation_policy=policy)
    alert = Alert.objects.create(
        service=service,
        source=Alert.SOURCE_GENERIC,
        external_id="alert-1",
        title="High latency",
        severity=Alert.SEVERITY_CRITICAL,
        raw_payload={},
        status=Alert.STATUS_FIRING,
        received_at=timezone.now(),
    )
    incident = Incident.objects.create(service=service, triggering_alert=alert, title=alert.title)
    return incident, user1, user2


@pytest.mark.django_db
def test_escalation_progresses_through_all_steps_then_exhausts(
    synchronous_escalation_chain, incident_with_two_step_policy
):
    incident, user1, user2 = incident_with_two_step_policy

    escalate_incident_step(incident.id, 0)

    incident.refresh_from_db()
    assert incident.status == Incident.STATUS_TRIGGERED
    assert incident.current_escalation_step == 1  # last step that actually ran

    attempts = NotificationAttempt.objects.filter(incident=incident).order_by(
        "escalation_step", "channel"
    )
    assert list(attempts.values_list("escalation_step", "user_id", "channel")) == [
        (0, user1.id, "slack"),
        (1, user2.id, "slack"),
        (1, user2.id, "sms"),
    ]

    events = list(TimelineEvent.objects.filter(incident=incident).order_by("id"))
    assert [e.event_type for e in events] == [
        TimelineEvent.EVENT_NOTIFICATION_SENT,  # step 0
        TimelineEvent.EVENT_ESCALATED,  # step 1
        TimelineEvent.EVENT_ESCALATED,  # exhausted (no repeats left)
    ]
    assert "never acknowledged" in events[-1].message.lower() or "exhausted" in events[-1].message.lower()


@pytest.mark.django_db
def test_escalation_repeats_policy_when_repeat_count_set(
    synchronous_escalation_chain, incident_with_two_step_policy
):
    incident, _user1, _user2 = incident_with_two_step_policy
    incident.service.escalation_policy.repeat_count = 1
    incident.service.escalation_policy.save(update_fields=["repeat_count"])

    escalate_incident_step(incident.id, 0)

    # 2 steps x 2 passes (1 repeat) = 4 escalation-related events, plus the
    # final exhausted note = 5.
    events = list(TimelineEvent.objects.filter(incident=incident).order_by("id"))
    assert len(events) == 5
    assert NotificationAttempt.objects.filter(incident=incident).count() == 6  # (1+2)*2


@pytest.mark.django_db
def test_acknowledged_incident_halts_escalation(
    synchronous_escalation_chain, incident_with_two_step_policy
):
    incident, _user1, _user2 = incident_with_two_step_policy
    incident.status = Incident.STATUS_ACKNOWLEDGED
    incident.save(update_fields=["status"])

    escalate_incident_step(incident.id, 0)

    assert NotificationAttempt.objects.filter(incident=incident).count() == 0
    assert TimelineEvent.objects.filter(incident=incident).count() == 0


@pytest.mark.django_db
def test_incident_becoming_acknowledged_mid_chain_stops_further_steps(
    synchronous_escalation_chain, incident_with_two_step_policy
):
    """The status re-check before each step is the *only* halt mechanism --
    prove a status flip between step 0 and step 1 stops step 1 from acting,
    without anything explicitly cancelling the scheduled Celery task."""
    incident, user1, _user2 = incident_with_two_step_policy

    def ack_before_next_hop(args=None, kwargs=None, countdown=None, **ignored):
        incident_id, next_step_order = args
        if next_step_order == 1:
            Incident.objects.filter(id=incident_id).update(status=Incident.STATUS_ACKNOWLEDGED)
        return escalate_incident_step(*(args or []), **(kwargs or {}))

    from unittest.mock import patch

    with patch.object(escalate_incident_step, "apply_async", side_effect=ack_before_next_hop):
        escalate_incident_step(incident.id, 0)

    attempts = NotificationAttempt.objects.filter(incident=incident)
    assert attempts.count() == 1
    assert attempts.first().user_id == user1.id  # only step 0's notification went out
