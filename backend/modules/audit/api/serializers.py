#Validation and read-only representation for audit search

from datetime import UTC

from rest_framework import serializers

from modules.audit.models import AuditEvent


class AuditSearchSerializer(serializers.Serializer):
    household = serializers.UUIDField(required=False)
    actor = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        if (
            attrs.get("date_from")
            and attrs.get("date_to")
            and attrs["date_from"] > attrs["date_to"]
        ):
            raise serializers.ValidationError(
                {"to": "The end date must not be before the start date."}
            )
        return attrs


class AuditEventSerializer(serializers.ModelSerializer):
    actor = serializers.UUIDField(source="actor_id", read_only=True)
    created_at = serializers.DateTimeField(default_timezone=UTC, read_only=True)

    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "actor",
            "actor_role",
            "action",
            "target_type",
            "target_id",
            "metadata",
            "created_at",
        )
        read_only_fields = fields
