# AI contribution: 50% or more AI-generated
"""HTTP types for browsing listings (US-36); visibility belongs to listings."""

from datetime import UTC
from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import APIException


class ListingPhotoUnavailable(APIException):
    status_code = 503
    default_detail = _("Photos are temporarily unavailable.")
    default_code = "photo_unavailable"


class BrowseFiltersSerializer(serializers.Serializer):
    """Optional filters. Leave a filter out of the query string to not use it."""

    category = serializers.CharField(
        required=False,
        max_length=64,
        help_text="A category code, as listed by GET /api/categories/.",
    )
    store = serializers.UUIDField(required=False, help_text="A store ID.")
    today = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Only listings that can still be picked up today, Montreal time.",
    )


class ListingStoreSerializer(serializers.Serializer):
    """The offering store; a listing's location is always its store's address."""

    id = serializers.UUIDField(source="store_id", read_only=True)
    name = serializers.CharField(source="store_name", read_only=True)
    street_number = serializers.CharField(source="store_street_number", read_only=True)
    street_name = serializers.CharField(source="store_street_name", read_only=True)
    unit = serializers.CharField(source="store_unit", read_only=True, allow_null=True)
    city = serializers.CharField(source="store_city", read_only=True)
    postal_code = serializers.CharField(source="store_postal_code", read_only=True)


class ListingCardSerializer(serializers.Serializer):
    """One card in the browse list, from ``listings.queries.browse_listings``."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    category = serializers.CharField(source="category_code", read_only=True)
    store = ListingStoreSerializer(source="*", read_only=True)
    # Times are UTC in the API; screens show them in Montreal time.
    pickup_start = serializers.DateTimeField(default_timezone=UTC, read_only=True)
    pickup_end = serializers.DateTimeField(default_timezone=UTC, read_only=True)
    units_left = serializers.IntegerField(read_only=True)
    unit = serializers.CharField(read_only=True)
    best_before = serializers.DateField(read_only=True, allow_null=True)
    photo_url = serializers.SerializerMethodField(allow_null=True)

    def get_photo_url(self, card: dict[str, Any]) -> str | None:
        """Cards were already scoped to the approved household by the query."""
        return self.context["photo_urls"].get(card.get("photo_ref"))


class BrowseErrorSerializer(serializers.Serializer):
    """The API's error shape: { code, message, fields }."""

    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
