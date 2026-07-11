import requests
from django.conf import settings

from .base import NotificationProvider, ProviderResult
from .exceptions import TransientProviderError


class SlackProvider(NotificationProvider):
    """Posts to the incident's team's per-team Incoming Webhook URL.

    Includes an interactive "Acknowledge" button (Slack Block Kit) whose
    click is verified and handled by SlackInteractivityView -- the confirmed
    product decision for v1 was interactive-in-Slack, not link-only.
    """

    def send(self, user, incident, message):
        team = incident.service.team
        webhook_url = team.slack_webhook_url
        if not webhook_url:
            return ProviderResult(
                success=False, error_message="Team has no Slack webhook URL configured."
            )

        incident_url = f"{settings.FRONTEND_BASE_URL}/incidents/{incident.id}"
        severity = incident.triggering_alert.severity.upper()

        payload = {
            "text": f"[{severity}] {incident.title}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*[{severity}] {incident.title}*\n{message}",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Acknowledge"},
                            "style": "primary",
                            "action_id": "acknowledge_incident",
                            "value": str(incident.id),
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Incident"},
                            "url": incident_url,
                        },
                    ],
                },
            ],
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
        except requests.RequestException as exc:
            raise TransientProviderError(str(exc)) from exc

        if response.status_code >= 500:
            raise TransientProviderError(
                f"Slack webhook returned {response.status_code}: {response.text[:500]}"
            )
        if response.status_code >= 400:
            return ProviderResult(
                success=False,
                error_message=f"Slack webhook returned {response.status_code}: {response.text[:500]}",
            )

        return ProviderResult(success=True)
