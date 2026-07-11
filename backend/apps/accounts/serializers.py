from rest_framework import serializers

from .models import Team, TeamMembership, User


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "slug", "slack_webhook_url", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class TeamMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = TeamMembership
        fields = ["id", "team", "user", "user_email", "role", "created_at"]
        read_only_fields = ["id", "team", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "timezone",
            "slack_user_id",
        ]
        read_only_fields = ["id"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
