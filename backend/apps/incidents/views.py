from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsTeamMember, TeamScopedQuerySetMixin

from .models import Incident
from .postmortem import generate_postmortem_markdown
from .serializers import IncidentDetailSerializer, IncidentSerializer, NoteSerializer
from .services import acknowledge_incident, add_note, resolve_incident


class IncidentViewSet(
    TeamScopedQuerySetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsTeamMember]
    team_field = "service__team"
    queryset = Incident.objects.select_related("service__team", "triggering_alert").order_by(
        "-created_at"
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return IncidentDetailSerializer
        return IncidentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if status_param := params.get("status"):
            qs = qs.filter(status=status_param)
        if service_param := params.get("service"):
            qs = qs.filter(service_id=service_param)
        if team_param := params.get("team"):
            qs = qs.filter(service__team_id=team_param)
        return qs

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        incident = self.get_object()
        acknowledge_incident(incident, actor=request.user)
        incident.refresh_from_db()
        return Response(IncidentDetailSerializer(incident).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        incident = self.get_object()
        resolve_incident(incident, actor=request.user)
        incident.refresh_from_db()
        return Response(IncidentDetailSerializer(incident).data)

    @action(detail=True, methods=["post"])
    def notes(self, request, pk=None):
        incident = self.get_object()
        serializer = NoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        add_note(incident, actor=request.user, message=serializer.validated_data["message"])
        return Response(status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def postmortem(self, request, pk=None):
        incident = self.get_object()
        return Response({"markdown": generate_postmortem_markdown(incident)})
