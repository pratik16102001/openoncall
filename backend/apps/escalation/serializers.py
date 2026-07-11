from rest_framework import serializers

from .models import EscalationPolicy, EscalationStep


class EscalationStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationStep
        fields = ["id", "order", "target_type", "target_id", "timeout_minutes", "notify_channels"]


class EscalationPolicySerializer(serializers.ModelSerializer):
    steps = EscalationStepSerializer(many=True, required=False)

    class Meta:
        model = EscalationPolicy
        fields = ["id", "team", "name", "repeat_count", "steps", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        policy = EscalationPolicy.objects.create(**validated_data)
        self._sync_steps(policy, steps_data)
        return policy

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if steps_data is not None:
            instance.steps.all().delete()
            self._sync_steps(instance, steps_data)
        return instance

    def _sync_steps(self, policy, steps_data):
        for step in steps_data:
            EscalationStep.objects.create(policy=policy, **step)
