from config.celery import app as celery_app


@celery_app.task
def send_notification(attempt_id):
    """Dispatches a NotificationAttempt to its provider.

    Stub for Phase 4 (the escalation engine just needs somewhere to enqueue
    to). Full provider dispatch -- Slack/Twilio/WebPush, retry/backoff,
    graceful failure on missing contact info -- lands in Phase 5.
    """
