from rest_framework import serializers


class NormalizedAlertSerializer(serializers.Serializer):
    """The common shape every source adapter must normalize into (Section 8)."""

    external_id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False, default="")
    severity = serializers.ChoiceField(choices=["critical", "warning", "info"])
    status = serializers.ChoiceField(choices=["firing", "resolved"])


def normalize_generic(payload):
    serializer = NormalizedAlertSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# Alertmanager, Datadog, CloudWatch, and Sentry adapters are added in Phase 8
# per Section 8's exact per-source field mapping.
ADAPTERS = {
    "generic": normalize_generic,
}


class UnsupportedSourceError(Exception):
    pass


def normalize_payload(source, payload):
    adapter = ADAPTERS.get(source)
    if adapter is None:
        raise UnsupportedSourceError(f"No adapter implemented for source '{source}'")
    return adapter(payload)
