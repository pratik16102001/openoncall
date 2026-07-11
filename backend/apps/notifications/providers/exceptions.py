class TransientProviderError(Exception):
    """Raised for retryable failures: network errors, 5xx from a provider.

    send_notification catches this specifically and retries with backoff.
    Anything else a provider returns as ProviderResult(success=False, ...)
    is treated as final -- the escalation engine's step timeout is the real
    fallback for those, not task-level retries (Section 6.3).
    """
