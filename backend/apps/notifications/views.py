import hashlib
import hmac
import json
import time

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.incidents.models import Incident
from apps.incidents.services import acknowledge_incident

from .models import PushSubscription

SLACK_TIMESTAMP_TOLERANCE_SECONDS = 60 * 5


class SlackInteractivityView(APIView):
    """Handles Slack's interactivity callback for the Acknowledge button.

    No DRF auth -- authenticity is established via Slack's request
    signature (HMAC-SHA256 over the raw body, using the app's signing
    secret), not a bearer credential.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not self._verify_signature(request):
            return HttpResponseForbidden("invalid signature")

        raw_payload = request.data.get("payload", "{}")
        payload = json.loads(raw_payload)
        actions = payload.get("actions") or []
        if not actions or actions[0].get("action_id") != "acknowledge_incident":
            return HttpResponse(status=200)

        incident_id = actions[0].get("value")
        incident = Incident.objects.filter(id=incident_id).first()
        if incident is None:
            return HttpResponse(status=200)

        slack_user_id = (payload.get("user") or {}).get("id")
        actor = User.objects.filter(slack_user_id=slack_user_id).first() if slack_user_id else None

        acknowledge_incident(incident, actor)
        return HttpResponse(status=200)

    def _verify_signature(self, request):
        secret = settings.SLACK_SIGNING_SECRET
        if not secret:
            return False

        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        try:
            if abs(time.time() - int(timestamp)) > SLACK_TIMESTAMP_TOLERANCE_SECONDS:
                return False
        except ValueError:
            return False

        base_string = f"v0:{timestamp}:{request.body.decode()}"
        computed = "v0=" + hmac.new(
            secret.encode(), base_string.encode(), hashlib.sha256
        ).hexdigest()
        slack_signature = request.headers.get("X-Slack-Signature", "")
        return hmac.compare_digest(computed, slack_signature)


class PushSubscriptionView(APIView):
    """POST from the frontend to register a browser's Web Push subscription."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription_info = request.data.get("subscription_info")
        if not subscription_info:
            return Response({"detail": "subscription_info is required."}, status=400)

        PushSubscription.objects.update_or_create(
            user=request.user,
            defaults={"subscription_info": subscription_info},
        )
        return Response(status=201)
