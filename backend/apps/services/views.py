from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsTeamMember, TeamOwnedCreateMixin, TeamScopedQuerySetMixin

from .models import Service, generate_integration_key
from .serializers import ServiceSerializer


class ServiceViewSet(TeamOwnedCreateMixin, TeamScopedQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, IsTeamMember]
    team_field = "team"
    queryset = Service.objects.select_related("team", "escalation_policy")

    def get_queryset(self):
        qs = super().get_queryset()
        if team_param := self.request.query_params.get("team"):
            qs = qs.filter(team_id=team_param)
        return qs

    @action(detail=True, methods=["post"], url_path="regenerate-key")
    def regenerate_key(self, request, pk=None):
        service = self.get_object()
        service.integration_key = generate_integration_key()
        service.save(update_fields=["integration_key", "updated_at"])
        return Response(self.get_serializer(service).data)
