from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsTeamMember, TeamOwnedCreateMixin, TeamScopedQuerySetMixin

from .models import EscalationPolicy
from .serializers import EscalationPolicySerializer


class EscalationPolicyViewSet(TeamOwnedCreateMixin, TeamScopedQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = EscalationPolicySerializer
    permission_classes = [IsAuthenticated, IsTeamMember]
    team_field = "team"
    queryset = EscalationPolicy.objects.select_related("team").prefetch_related("steps")

    def get_queryset(self):
        qs = super().get_queryset()
        if team_param := self.request.query_params.get("team"):
            qs = qs.filter(team_id=team_param)
        return qs
