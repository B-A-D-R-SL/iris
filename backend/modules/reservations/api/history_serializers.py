# AI contribution: 50% or more AI-generated
"""HTTP types for the pickup history (US-48); the order belongs to queries."""

from datetime import UTC

from rest_framework import serializers

from modules.reservations.api.serializers import ListingStoreSerializer
from modules.reservations.models import ReservationStatus


class HistoryFiltersSerializer(serializers.Serializer):
    """Optional filter. Leave it out of the query string to see every status."""

    status = serializers.ChoiceField(
        choices=ReservationStatus.choices,
        required=False,
        help_text="Only reservations with this status.",
    )
    as_of = serializers.DateTimeField(
        required=False,
        help_text="The time page 1 was read, from its next link: later pages "
        "keep that order. Leave it out for page 1; a future time counts as now.",
    )


class HistoryEntrySerializer(serializers.Serializer):
    """One reservation of the household, from ``queries.history_entries``."""

    id = serializers.UUIDField(read_only=True)
    status = serializers.ChoiceField(choices=ReservationStatus.choices, read_only=True)
    upcoming = serializers.BooleanField(
        read_only=True,
        help_text="True while it can still be picked up: reserved, and the "
        "pickup window not ended.",
    )
    title = serializers.CharField(read_only=True, help_text="The listing's title.")
    unit = serializers.CharField(read_only=True, help_text="item or bundle.")
    quantity = serializers.IntegerField(read_only=True)
    store = ListingStoreSerializer(source="*", read_only=True)
    # Times are UTC in the API; screens show them in Montreal time.
    pickup_start = serializers.DateTimeField(default_timezone=UTC, read_only=True)
    pickup_end = serializers.DateTimeField(default_timezone=UTC, read_only=True)
    picked_up_at = serializers.DateTimeField(
        default_timezone=UTC,
        read_only=True,
        allow_null=True,
        help_text="When the store confirmed the pickup; null until then.",
    )
    pickup_code = serializers.CharField(
        read_only=True,
        allow_null=True,
        help_text="The code to show at the store; null once it is not upcoming.",
    )
