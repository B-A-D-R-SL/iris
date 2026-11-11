# AI contribution: 50% or more AI-generated
"""Pickup lookup input and the pickup summary store staff see (US-44)."""

from datetime import UTC
from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from modules.reservations.domain.pickup import normalize_code
from modules.reservations.models import Reservation, ReservationStatus

CODE_LENGTH = Reservation._meta.get_field("pickup_code").max_length


class PickupLookupSerializer(serializers.Serializer):
    """A typed or scanned pickup code; spaces and lowercase are accepted."""

    code = serializers.CharField(max_length=32)

    def validate_code(self, value: str) -> str:
        """Normalize, then require exactly the stored code length in letters/digits."""
        code = normalize_code(value)
        if len(code) != CODE_LENGTH or not (code.isascii() and code.isalnum()):
            raise serializers.ValidationError(
                _("Enter the %(length)s-character pickup code.")
                % {"length": CODE_LENGTH}
            )
        return code


class PickupSerializer(serializers.Serializer):
    """First name and last initial only; no phone, email or address."""

    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=ReservationStatus.choices)
    holder = serializers.CharField(allow_null=True)
    alternate = serializers.CharField(allow_null=True)
    title = serializers.CharField()
    unit = serializers.CharField()
    quantity = serializers.IntegerField()
    pickup_code = serializers.CharField()
    pickup_start = serializers.DateTimeField(default_timezone=UTC)
    pickup_end = serializers.DateTimeField(default_timezone=UTC)
    picked_up_at = serializers.DateTimeField(allow_null=True, default_timezone=UTC)


class PickupErrorSerializer(serializers.Serializer):
    """The shared ``{code, message, fields}`` error, plus the first pickup time."""

    code = serializers.CharField()
    message = serializers.CharField()
    fields: Any = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
    picked_up_at = serializers.DateTimeField(
        allow_null=True, required=False, default_timezone=UTC
    )
