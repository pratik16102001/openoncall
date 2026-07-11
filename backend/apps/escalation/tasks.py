from celery import shared_task


@shared_task
def escalate_incident_step(incident_id, step_order, repeats_remaining=None):
    """Entry point for the escalation engine.

    Stub for Phase 3 (alert ingestion just needs to be able to enqueue this).
    Full implementation -- per-step notification fan-out, timeout-based
    chaining to the next step, repeat handling -- lands in Phase 4.
    """
