from config.celery import app as celery_app

from .models import NotificationAttempt
from .providers import PROVIDERS, TransientProviderError


def _build_message(incident):
    alert = incident.triggering_alert
    return f"[{alert.severity.upper()}] {incident.title} ({incident.service.name})"


@celery_app.task(bind=True, max_retries=3, retry_backoff=True)
def send_notification(self, attempt_id):
    """Dispatches a NotificationAttempt to its provider.

    Retries (exponential backoff, max 3) only for TransientProviderError --
    network errors / 5xx from the provider. Everything else (missing
    contact info, invalid destination, 4xx) is a final failure: log it and
    move on, since the escalation engine's step-timeout fallback to the
    next step/channel is the real safety net here, not task-level retries
    (Section 6.3).
    """
    attempt = (
        NotificationAttempt.objects.filter(id=attempt_id)
        .select_related("incident__service", "incident__triggering_alert", "user")
        .first()
    )
    if attempt is None:
        return

    provider_cls = PROVIDERS.get(attempt.channel)
    if provider_cls is None:
        attempt.status = NotificationAttempt.STATUS_FAILED
        attempt.error_message = f"No provider registered for channel '{attempt.channel}'."
        attempt.save(update_fields=["status", "error_message", "updated_at"])
        return

    message = _build_message(attempt.incident)

    try:
        result = provider_cls().send(attempt.user, attempt.incident, message)
    except TransientProviderError as exc:
        raise self.retry(exc=exc)

    if result.success:
        attempt.status = NotificationAttempt.STATUS_SENT
        attempt.provider_message_id = result.provider_message_id
    else:
        attempt.status = NotificationAttempt.STATUS_FAILED
        attempt.error_message = result.error_message
    attempt.save(update_fields=["status", "provider_message_id", "error_message", "updated_at"])
