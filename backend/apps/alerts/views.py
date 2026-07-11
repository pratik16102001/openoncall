from django.http import Http404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.services.models import Service

from .adapters import normalize_payload
from .services import ingest_alert


class AlertWebhookView(APIView):
    """Handles POST /webhooks/<source>/<integration_key>/.

    No DRF auth -- the integration_key in the URL is itself the bearer
    credential. A missing/invalid key and a missing service both resolve to
    a bare 404, so probing the endpoint can't distinguish a valid key from
    an invalid one.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    source = None  # bound per-URL via as_view(source=...)

    def post(self, request, integration_key):
        service = Service.objects.filter(integration_key=integration_key).first()
        if service is None:
            raise Http404

        normalized = normalize_payload(self.source, request.data)
        alert, incident, created = ingest_alert(
            service=service,
            source=self.source,
            normalized=normalized,
            raw_payload=request.data,
        )
        return Response(
            {"status": "ok"}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
