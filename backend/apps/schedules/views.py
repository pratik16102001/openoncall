from django.utils import timezone as django_timezone
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsTeamMember, TeamOwnedCreateMixin, TeamScopedQuerySetMixin

from .models import Schedule
from .serializers import ScheduleOverrideSerializer, ScheduleSerializer
from .services import get_current_on_call


class ScheduleViewSet(TeamOwnedCreateMixin, TeamScopedQuerySetMixin, viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    permission_classes = [IsAuthenticated, IsTeamMember]
    team_field = "team"
    queryset = Schedule.objects.select_related("team").prefetch_related(
        "schedule_participants__user", "overrides"
    )

    def get_queryset(self):
        qs = super().get_queryset()
        if team_param := self.request.query_params.get("team"):
            qs = qs.filter(team_id=team_param)
        return qs

    @action(detail=True, methods=["get"], url_path="on-call")
    def on_call(self, request, pk=None):
        schedule = self.get_object()

        at_param = request.query_params.get("at")
        at_time = None
        if at_param:
            at_time = parse_datetime(at_param)
            if at_time is None:
                return Response({"detail": "invalid `at` datetime, expected ISO-8601."}, status=400)
            if django_timezone.is_naive(at_time):
                at_time = django_timezone.make_aware(at_time, django_timezone.utc)

        user = get_current_on_call(schedule, at_time)
        if user is None:
            return Response({"user": None})
        return Response({"user": {"id": user.id, "email": user.email}})

    @action(detail=True, methods=["post"], url_path="overrides")
    def overrides(self, request, pk=None):
        schedule = self.get_object()
        serializer = ScheduleOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(schedule=schedule)
        return Response(serializer.data, status=201)
