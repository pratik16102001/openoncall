import hashlib
import json

from rest_framework import serializers


class NormalizedAlertSerializer(serializers.Serializer):
    """The common shape every source adapter must normalize into (Section 8)."""

    external_id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False, default="")
    severity = serializers.ChoiceField(choices=["critical", "warning", "info"])
    status = serializers.ChoiceField(choices=["firing", "resolved"])


def _validate(data):
    serializer = NormalizedAlertSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def normalize_generic(payload):
    """The documented public contract, as-is -- one alert per request."""
    return [(_validate(payload), payload)]


def normalize_alertmanager(payload):
    """Alertmanager batches multiple alerts per webhook call in `alerts`,
    so this (uniquely among the adapters) can return more than one item.
    """
    results = []
    for alert in payload.get("alerts", []):
        labels = alert.get("labels", {}) or {}
        annotations = alert.get("annotations", {}) or {}

        severity = labels.get("severity", "warning")
        if severity not in ("critical", "warning", "info"):
            severity = "warning"

        alert_status = alert.get("status", "firing")
        if alert_status not in ("firing", "resolved"):
            alert_status = "firing"

        normalized = _validate(
            {
                "external_id": alert.get("fingerprint", ""),
                "title": labels.get("alertname", "Alertmanager alert"),
                "description": annotations.get("description") or annotations.get("summary", ""),
                "severity": severity,
                "status": alert_status,
            }
        )
        results.append((normalized, alert))
    return results


def normalize_datadog(payload):
    external_id = payload.get("id")
    if not external_id:
        raw = f"{payload.get('alert_id', '')}{payload.get('title', '')}"
        external_id = hashlib.sha256(raw.encode()).hexdigest()

    alert_type = (payload.get("alert_type") or "").lower()
    if alert_type in ("error", "critical"):
        severity = "critical"
    elif alert_type == "warning":
        severity = "warning"
    else:
        severity = "info"

    transition = payload.get("transition")
    alert_status = "resolved" if transition == "Recovered" else "firing"

    normalized = _validate(
        {
            "external_id": str(external_id),
            "title": payload.get("title", ""),
            "description": payload.get("body", ""),
            "severity": severity,
            "status": alert_status,
        }
    )
    return [(normalized, payload)]


def normalize_cloudwatch(payload):
    """CloudWatch alarms arrive via an SNS envelope -- the actual alarm
    state is a JSON string in the `Message` field."""
    message_raw = payload.get("Message", "{}")
    message = json.loads(message_raw) if isinstance(message_raw, str) else (message_raw or {})

    new_state = message.get("NewStateValue")
    alert_status = "resolved" if new_state == "OK" else "firing"

    alarm_name = message.get("AlarmName", "")
    lowered = alarm_name.lower()
    if "critical" in lowered:
        severity = "critical"
    elif "info" in lowered:
        severity = "info"
    else:
        severity = "warning"

    normalized = _validate(
        {
            "external_id": message.get("AlarmArn", ""),
            "title": alarm_name,
            "description": message.get("NewStateReason", ""),
            "severity": severity,
            "status": alert_status,
        }
    )
    return [(normalized, message)]


def normalize_sentry(payload):
    event = payload.get("event") or {}
    issue = payload.get("issue") or {}

    external_id = event.get("event_id") or issue.get("id") or ""
    title = event.get("title") or issue.get("title") or ""
    description = event.get("culprit") or issue.get("culprit") or ""

    level = (event.get("level") or issue.get("level") or "").lower()
    if level in ("fatal", "error"):
        severity = "critical"
    elif level == "warning":
        severity = "warning"
    else:
        severity = "info"

    normalized = _validate(
        {
            "external_id": str(external_id),
            "title": title,
            "description": description,
            "severity": severity,
            # Sentry issue webhooks don't send a resolve state the same way
            # other sources do -- resolution here is manual via the UI.
            "status": "firing",
        }
    )
    return [(normalized, payload)]


ADAPTERS = {
    "generic": normalize_generic,
    "alertmanager": normalize_alertmanager,
    "datadog": normalize_datadog,
    "cloudwatch": normalize_cloudwatch,
    "sentry": normalize_sentry,
}


class UnsupportedSourceError(Exception):
    pass


def normalize_payload(source, payload):
    """Returns a list of (normalized, raw_item) pairs -- always a list,
    even for sources that only ever produce one alert per request, so the
    caller doesn't need to special-case Alertmanager's batching.
    """
    adapter = ADAPTERS.get(source)
    if adapter is None:
        raise UnsupportedSourceError(f"No adapter implemented for source '{source}'")
    return adapter(payload)
