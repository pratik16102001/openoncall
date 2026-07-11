import json

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Team
from apps.alerts.models import Alert
from apps.escalation.models import EscalationPolicy
from apps.incidents.models import Incident
from apps.services.models import Service


@pytest.fixture
def service(db):
    team = Team.objects.create(name="Platform", slug="platform")
    policy = EscalationPolicy.objects.create(team=team, name="Default")
    return Service.objects.create(team=team, name="checkout-api", escalation_policy=policy)


# --- Alertmanager --------------------------------------------------------------

ALERTMANAGER_PAYLOAD = {
    "receiver": "webhook",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "HighLatency", "severity": "critical", "instance": "web-1"},
            "annotations": {
                "summary": "High latency detected",
                "description": "p99 latency above 2s for 5 minutes",
            },
            "startsAt": "2026-01-01T00:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "abc123fingerprint",
        },
        {
            "status": "firing",
            "labels": {"alertname": "DiskSpaceLow", "severity": "unrecognized-value", "instance": "db-1"},
            "annotations": {"summary": "Disk space below 10%"},
            "startsAt": "2026-01-01T00:05:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "fingerprint": "def456fingerprint",
        },
    ],
    "groupLabels": {},
    "commonLabels": {},
    "commonAnnotations": {},
    "externalURL": "http://alertmanager:9093",
}


@pytest.mark.django_db
def test_alertmanager_webhook_creates_one_incident_per_alert(service):
    resp = APIClient().post(
        f"/webhooks/alertmanager/{service.integration_key}/", ALERTMANAGER_PAYLOAD, format="json"
    )
    assert resp.status_code == 201
    assert resp.json()["processed"] == 2

    assert Alert.objects.count() == 2
    assert Incident.objects.count() == 2

    high_latency = Alert.objects.get(external_id="abc123fingerprint")
    assert high_latency.title == "HighLatency"
    assert high_latency.description == "p99 latency above 2s for 5 minutes"  # description wins over summary
    assert high_latency.severity == "critical"
    assert high_latency.status == "firing"

    disk_space = Alert.objects.get(external_id="def456fingerprint")
    assert disk_space.severity == "warning"  # unrecognized severity value maps to warning


@pytest.mark.django_db
def test_alertmanager_resolved_status_resolves_incident(service):
    APIClient().post(f"/webhooks/alertmanager/{service.integration_key}/", ALERTMANAGER_PAYLOAD, format="json")

    resolved_payload = json.loads(json.dumps(ALERTMANAGER_PAYLOAD))
    resolved_payload["alerts"] = [{**ALERTMANAGER_PAYLOAD["alerts"][0], "status": "resolved"}]
    resp = APIClient().post(
        f"/webhooks/alertmanager/{service.integration_key}/", resolved_payload, format="json"
    )
    assert resp.status_code == 200

    incident = Incident.objects.get(triggering_alert__external_id="abc123fingerprint")
    assert incident.status == Incident.STATUS_RESOLVED


# --- Datadog -----------------------------------------------------------------

DATADOG_PAYLOAD = {
    "id": "1234567",
    "alert_id": "987654",
    "title": "[Triggered] High CPU on web-1",
    "body": "CPU usage above 90% for 5 minutes",
    "alert_type": "error",
    "transition": "Triggered",
    "date": 1735689600000,
}


@pytest.mark.django_db
def test_datadog_webhook_creates_incident(service):
    resp = APIClient().post(f"/webhooks/datadog/{service.integration_key}/", DATADOG_PAYLOAD, format="json")
    assert resp.status_code == 201

    alert = Alert.objects.get()
    assert alert.external_id == "1234567"
    assert alert.title == DATADOG_PAYLOAD["title"]
    assert alert.description == DATADOG_PAYLOAD["body"]
    assert alert.severity == "critical"  # alert_type "error" -> critical
    assert alert.status == "firing"


@pytest.mark.django_db
def test_datadog_recovered_transition_resolves_incident(service):
    APIClient().post(f"/webhooks/datadog/{service.integration_key}/", DATADOG_PAYLOAD, format="json")

    recovered = {**DATADOG_PAYLOAD, "transition": "Recovered", "title": "[Recovered] High CPU on web-1"}
    resp = APIClient().post(f"/webhooks/datadog/{service.integration_key}/", recovered, format="json")
    assert resp.status_code == 200

    incident = Incident.objects.get()
    assert incident.status == Incident.STATUS_RESOLVED


@pytest.mark.django_db
def test_datadog_missing_id_falls_back_to_hash(service):
    payload = {k: v for k, v in DATADOG_PAYLOAD.items() if k != "id"}
    resp = APIClient().post(f"/webhooks/datadog/{service.integration_key}/", payload, format="json")
    assert resp.status_code == 201
    alert = Alert.objects.get()
    assert alert.external_id  # a hash was generated
    assert alert.external_id != "1234567"


# --- CloudWatch (via SNS) --------------------------------------------------------

CLOUDWATCH_MESSAGE = {
    "AlarmName": "CriticalHighCPU",
    "AlarmDescription": None,
    "AWSAccountId": "123456789012",
    "NewStateValue": "ALARM",
    "NewStateReason": "Threshold Crossed: 1 datapoint [95.0] was greater than the threshold (90.0)",
    "StateChangeTime": "2026-01-01T00:00:00.000+0000",
    "Region": "US East (N. Virginia)",
    "AlarmArn": "arn:aws:cloudwatch:us-east-1:123456789012:alarm:CriticalHighCPU",
    "OldStateValue": "OK",
}

CLOUDWATCH_SNS_ENVELOPE = {
    "Type": "Notification",
    "MessageId": "abc-def-ghi",
    "TopicArn": "arn:aws:sns:us-east-1:123456789012:my-topic",
    "Subject": 'ALARM: "CriticalHighCPU" in US East (N. Virginia)',
    "Message": json.dumps(CLOUDWATCH_MESSAGE),
    "Timestamp": "2026-01-01T00:00:00.000Z",
    "SignatureVersion": "1",
    "Signature": "sig",
    "SigningCertURL": "https://sns.example.com/cert.pem",
    "UnsubscribeURL": "https://sns.example.com/unsubscribe",
}


@pytest.mark.django_db
def test_cloudwatch_webhook_creates_incident(service):
    resp = APIClient().post(
        f"/webhooks/cloudwatch/{service.integration_key}/", CLOUDWATCH_SNS_ENVELOPE, format="json"
    )
    assert resp.status_code == 201

    alert = Alert.objects.get()
    assert alert.external_id == CLOUDWATCH_MESSAGE["AlarmArn"]
    assert alert.title == "CriticalHighCPU"
    assert alert.description == CLOUDWATCH_MESSAGE["NewStateReason"]
    assert alert.severity == "critical"  # "critical" in alarm name
    assert alert.status == "firing"


@pytest.mark.django_db
def test_cloudwatch_ok_state_resolves_incident(service):
    APIClient().post(f"/webhooks/cloudwatch/{service.integration_key}/", CLOUDWATCH_SNS_ENVELOPE, format="json")

    ok_message = {**CLOUDWATCH_MESSAGE, "NewStateValue": "OK", "OldStateValue": "ALARM"}
    ok_envelope = {**CLOUDWATCH_SNS_ENVELOPE, "Message": json.dumps(ok_message)}
    resp = APIClient().post(f"/webhooks/cloudwatch/{service.integration_key}/", ok_envelope, format="json")
    assert resp.status_code == 200

    incident = Incident.objects.get()
    assert incident.status == Incident.STATUS_RESOLVED


# --- Sentry ----------------------------------------------------------------------

SENTRY_PAYLOAD = {
    "action": "created",
    "event": {
        "event_id": "929f8d9f7a1a4b2eae0e5b8f0e8c1234",
        "title": "ZeroDivisionError: division by zero",
        "culprit": "myapp.views in checkout",
        "level": "error",
    },
    "issue": {
        "id": "5555555555",
        "title": "ZeroDivisionError: division by zero",
        "culprit": "myapp.views in checkout",
        "level": "error",
    },
}


@pytest.mark.django_db
def test_sentry_webhook_creates_incident(service):
    resp = APIClient().post(f"/webhooks/sentry/{service.integration_key}/", SENTRY_PAYLOAD, format="json")
    assert resp.status_code == 201

    alert = Alert.objects.get()
    assert alert.external_id == SENTRY_PAYLOAD["event"]["event_id"]
    assert alert.title == "ZeroDivisionError: division by zero"
    assert alert.description == "myapp.views in checkout"
    assert alert.severity == "critical"  # level "error" -> critical
    assert alert.status == "firing"  # Sentry never sends a resolve state


@pytest.mark.django_db
def test_sentry_webhook_falls_back_to_issue_when_no_event(service):
    payload = {"action": "created", "issue": SENTRY_PAYLOAD["issue"]}
    resp = APIClient().post(f"/webhooks/sentry/{service.integration_key}/", payload, format="json")
    assert resp.status_code == 201
    alert = Alert.objects.get()
    assert alert.external_id == SENTRY_PAYLOAD["issue"]["id"]
