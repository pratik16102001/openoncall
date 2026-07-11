import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from apps.accounts.models import Team, User
from apps.alerts.models import Alert
from apps.escalation.models import EscalationPolicy
from apps.incidents.models import Incident, TimelineEvent
from apps.notifications.models import NotificationAttempt
from apps.notifications.providers.exceptions import TransientProviderError
from apps.notifications.providers.slack import SlackProvider
from apps.notifications.providers.twilio_provider import TwilioSMSProvider
from apps.notifications.providers.webpush_provider import WebPushProvider
from apps.notifications.tasks import send_notification
from apps.services.models import Service


@pytest.fixture
def incident(db):
    team = Team.objects.create(name="Platform", slug="platform", slack_webhook_url="https://hooks.slack.test/x")
    policy = EscalationPolicy.objects.create(team=team, name="Default")
    service = Service.objects.create(team=team, name="checkout-api", escalation_policy=policy)
    alert = Alert.objects.create(
        service=service,
        source=Alert.SOURCE_GENERIC,
        external_id="a1",
        title="High latency",
        severity=Alert.SEVERITY_CRITICAL,
        raw_payload={},
        status=Alert.STATUS_FIRING,
        received_at=timezone.now(),
    )
    return Incident.objects.create(service=service, triggering_alert=alert, title=alert.title)


@pytest.fixture
def user(db):
    return User.objects.create_user(email="oncall@example.com", password="pw12345")


# --- SlackProvider -----------------------------------------------------------


@pytest.mark.django_db
def test_slack_provider_posts_message_with_acknowledge_button(incident, user):
    with patch("apps.notifications.providers.slack.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        result = SlackProvider().send(user, incident, "test message")

    assert result.success
    _args, kwargs = mock_post.call_args
    payload = kwargs["json"]
    button = payload["blocks"][1]["elements"][0]
    assert button["action_id"] == "acknowledge_incident"
    assert button["value"] == str(incident.id)


@pytest.mark.django_db
def test_slack_provider_fails_gracefully_without_team_webhook(user):
    team = Team.objects.create(name="No Slack", slug="no-slack")
    policy = EscalationPolicy.objects.create(team=team, name="Default")
    service = Service.objects.create(team=team, name="svc", escalation_policy=policy)
    alert = Alert.objects.create(
        service=service,
        source=Alert.SOURCE_GENERIC,
        external_id="a2",
        title="t",
        severity=Alert.SEVERITY_WARNING,
        raw_payload={},
        status=Alert.STATUS_FIRING,
        received_at=timezone.now(),
    )
    incident = Incident.objects.create(service=service, triggering_alert=alert, title=alert.title)

    result = SlackProvider().send(user, incident, "test message")

    assert not result.success
    assert "webhook" in result.error_message.lower()


@pytest.mark.django_db
def test_slack_provider_raises_transient_error_on_5xx(incident, user):
    with patch("apps.notifications.providers.slack.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=503, text="unavailable")
        with pytest.raises(TransientProviderError):
            SlackProvider().send(user, incident, "test message")


# --- TwilioSMSProvider ---------------------------------------------------------


@pytest.mark.django_db
def test_twilio_sms_fails_gracefully_without_phone_number(incident, user):
    assert user.phone_number in (None, "")
    result = TwilioSMSProvider().send(user, incident, "test message")
    assert not result.success
    assert "phone_number" in result.error_message


# --- WebPushProvider ------------------------------------------------------------


@pytest.mark.django_db
def test_webpush_fails_gracefully_without_subscription(incident, user):
    result = WebPushProvider().send(user, incident, "test message")
    assert not result.success
    assert "subscription" in result.error_message.lower()


# --- send_notification task --------------------------------------------------


@pytest.mark.django_db
def test_send_notification_marks_failed_without_crashing_on_missing_contact_info(incident, user):
    attempt = NotificationAttempt.objects.create(
        incident=incident, escalation_step=0, user=user, channel=NotificationAttempt.CHANNEL_SMS
    )

    send_notification.apply(args=[attempt.id])

    attempt.refresh_from_db()
    assert attempt.status == NotificationAttempt.STATUS_FAILED
    assert attempt.error_message


@pytest.mark.django_db
def test_send_notification_marks_sent_on_provider_success(incident, user):
    attempt = NotificationAttempt.objects.create(
        incident=incident, escalation_step=0, user=user, channel=NotificationAttempt.CHANNEL_SLACK
    )

    with patch("apps.notifications.providers.slack.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, text="ok")
        send_notification.apply(args=[attempt.id])

    attempt.refresh_from_db()
    assert attempt.status == NotificationAttempt.STATUS_SENT


@pytest.mark.django_db
def test_send_notification_retries_on_transient_failure(incident, user):
    from celery.exceptions import Retry

    attempt = NotificationAttempt.objects.create(
        incident=incident, escalation_step=0, user=user, channel=NotificationAttempt.CHANNEL_SLACK
    )

    with patch(
        "apps.notifications.providers.slack.SlackProvider.send",
        side_effect=TransientProviderError("connection reset"),
    ):
        with pytest.raises(Retry):
            send_notification.apply(args=[attempt.id])

    attempt.refresh_from_db()
    # A transient failure is retryable, not terminal -- it must not be
    # marked "failed" (that would make the operator think it's done for).
    assert attempt.status == NotificationAttempt.STATUS_PENDING


# --- Slack interactivity endpoint (Acknowledge button) ------------------------


def _sign(secret, timestamp, body):
    base_string = f"v0:{timestamp}:{body}"
    return "v0=" + hmac.new(secret.encode(), base_string.encode(), hashlib.sha256).hexdigest()


@pytest.mark.django_db
@override_settings(SLACK_SIGNING_SECRET="test-signing-secret")
def test_slack_acknowledge_button_acknowledges_incident(incident):
    slack_user = User.objects.create_user(
        email="slackuser@example.com", password="pw12345", slack_user_id="U123"
    )
    payload = {
        "actions": [{"action_id": "acknowledge_incident", "value": str(incident.id)}],
        "user": {"id": "U123"},
    }
    body = f"payload={json.dumps(payload)}"
    timestamp = str(int(time.time()))
    signature = _sign("test-signing-secret", timestamp, body)

    client = Client()
    resp = client.post(
        "/webhooks/slack/interactivity/",
        data=body,
        content_type="application/x-www-form-urlencoded",
        HTTP_X_SLACK_REQUEST_TIMESTAMP=timestamp,
        HTTP_X_SLACK_SIGNATURE=signature,
    )

    assert resp.status_code == 200
    incident.refresh_from_db()
    assert incident.status == Incident.STATUS_ACKNOWLEDGED
    assert incident.assigned_to == slack_user
    assert TimelineEvent.objects.filter(
        incident=incident, event_type=TimelineEvent.EVENT_ACKNOWLEDGED
    ).exists()


@pytest.mark.django_db
@override_settings(SLACK_SIGNING_SECRET="test-signing-secret")
def test_slack_interactivity_rejects_bad_signature(incident):
    payload = {
        "actions": [{"action_id": "acknowledge_incident", "value": str(incident.id)}],
        "user": {"id": "U123"},
    }
    body = f"payload={json.dumps(payload)}"
    timestamp = str(int(time.time()))

    client = Client()
    resp = client.post(
        "/webhooks/slack/interactivity/",
        data=body,
        content_type="application/x-www-form-urlencoded",
        HTTP_X_SLACK_REQUEST_TIMESTAMP=timestamp,
        HTTP_X_SLACK_SIGNATURE="v0=deadbeef",
    )

    assert resp.status_code == 403
    incident.refresh_from_db()
    assert incident.status == Incident.STATUS_TRIGGERED
