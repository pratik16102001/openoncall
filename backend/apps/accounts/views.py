from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Team, TeamMembership
from .permissions import IsTeamMember
from .serializers import LoginSerializer, TeamMembershipSerializer, TeamSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class TeamViewSet(viewsets.ModelViewSet):
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated, IsTeamMember]

    def get_queryset(self):
        return Team.objects.filter(memberships__user=self.request.user).distinct()

    def get_permissions(self):
        # Any authenticated user may create a team (and becomes its first
        # admin); object-level team membership is enforced for everything
        # else via IsTeamMember + the queryset scoping above.
        if self.action == "create":
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        team = serializer.save()
        TeamMembership.objects.create(team=team, user=self.request.user, role=TeamMembership.ROLE_ADMIN)

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        team = self.get_object()

        if request.method == "GET":
            memberships = team.memberships.select_related("user")
            return Response(TeamMembershipSerializer(memberships, many=True).data)

        requester_membership = team.memberships.filter(user=request.user).first()
        if not requester_membership or requester_membership.role != TeamMembership.ROLE_ADMIN:
            return Response(
                {"detail": "Only team admins can add members."}, status=status.HTTP_403_FORBIDDEN
            )

        serializer = TeamMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(team=team)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
