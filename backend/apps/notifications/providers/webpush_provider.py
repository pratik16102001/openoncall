import json

from django.conf import settings
from pywebpush import WebPushException, webpush

from apps.notifications.models import PushSubscription

from .base import NotificationProvider, ProviderResult
from .exceptions import TransientProviderError


class WebPushProvider(NotificationProvider):
    def send(self, user, incident, message):
        subscription = PushSubscription.objects.filter(user=user).first()
        if subscription is None:
            return ProviderResult(
                success=False, error_message="User has no registered push subscription."
            )
        if not (settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY):
            return ProviderResult(
                success=False, error_message="Web Push is not configured on this instance."
            )

        try:
            webpush(
                subscription_info=subscription.subscription_info,
                data=json.dumps({"title": incident.title, "body": message}),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code and status_code >= 500:
                raise TransientProviderError(str(exc)) from exc
            return ProviderResult(success=False, error_message=str(exc))

        return ProviderResult(success=True)
