from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .models import Team, TeamMembership


class IsTeamMember(BasePermission):
    """Object-level permission: request.user must belong to the object's team.

    Objects are expected to expose their owning Team either directly as a
    `team` attribute, indirectly via a `get_team()` method (for models that
    reach team scoping through a relation, e.g. Incident -> Service -> Team),
    or *be* a Team themselves.
    """

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Team):
            team = obj
        elif hasattr(obj, "get_team"):
            team = obj.get_team()
        else:
            team = getattr(obj, "team", None)

        if team is None:
            return False
        return TeamMembership.objects.filter(team=team, user=request.user).exists()


class TeamScopedQuerySetMixin:
    """Filters a viewset's queryset down to the requesting user's teams.

    Subclasses set `team_field` to the ORM lookup path from the model to its
    owning Team (e.g. "team" or "service__team"). Combine with IsTeamMember
    for object-level enforcement on retrieve/update/delete.
    """

    team_field = "team"

    def get_queryset(self):
        qs = super().get_queryset()
        user_teams = TeamMembership.objects.filter(user=self.request.user).values_list(
            "team_id", flat=True
        )
        return qs.filter(**{f"{self.team_field}__in": user_teams}).distinct()


class TeamOwnedCreateMixin:
    """Guards the `create` action for resources that carry a writable `team`
    field directly in the request body (Schedule, EscalationPolicy,
    Service). IsTeamMember is an object-level check -- it can't stop a
    client from POSTing an arbitrary team id it doesn't belong to, since
    there's no object yet at create time. This closes that gap.
    """

    def perform_create(self, serializer):
        team = serializer.validated_data.get("team")
        if team is None or not TeamMembership.objects.filter(team=team, user=self.request.user).exists():
            raise PermissionDenied("You are not a member of this team.")
        serializer.save()
