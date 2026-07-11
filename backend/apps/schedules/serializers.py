from rest_framework import serializers

from .models import Schedule, ScheduleOverride, ScheduleParticipant


class ScheduleParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleParticipant
        fields = ["id", "user", "order"]


class ScheduleOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleOverride
        fields = ["id", "schedule", "user", "start_time", "end_time", "reason"]
        read_only_fields = ["id", "schedule"]


class ScheduleSerializer(serializers.ModelSerializer):
    participants = ScheduleParticipantSerializer(source="schedule_participants", many=True, required=False)

    class Meta:
        model = Schedule
        fields = [
            "id",
            "team",
            "name",
            "timezone",
            "rotation_type",
            "rotation_start",
            "rotation_length_hours",
            "participants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        participants_data = validated_data.pop("schedule_participants", [])
        schedule = Schedule.objects.create(**validated_data)
        self._sync_participants(schedule, participants_data)
        return schedule

    def update(self, instance, validated_data):
        participants_data = validated_data.pop("schedule_participants", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if participants_data is not None:
            instance.schedule_participants.all().delete()
            self._sync_participants(instance, participants_data)
        return instance

    def _sync_participants(self, schedule, participants_data):
        for participant in participants_data:
            ScheduleParticipant.objects.create(schedule=schedule, **participant)
