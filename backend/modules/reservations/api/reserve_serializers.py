# AI contribution: 50% or more AI-generated
"""HTTP types for reserving (US-41); the rules belong to services and domain."""

from datetime import UTC

from rest_framework import serializers

# The largest max per household a listing can have (listings.models).
MAX_QUANTITY = 10


class ReserveInputSerializer(serializers.Serializer):
    """What the household sends: which listing, and how many units."""

    listing_id = serializers.UUIDField()
    quantity = serializers.IntegerField(
        min_value=1,
        max_value=MAX_QUANTITY,
        default=1,
        help_text="Units to reserve; at most the listing's max per household.",
    )


class ReservationSerializer(serializers.Serializer):
    """The reservation just made, with the code to show at the store."""

    id = serializers.UUIDField(read_only=True)
    listing_id = serializers.UUIDField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    pickup_code = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(default_timezone=UTC, read_only=True)
