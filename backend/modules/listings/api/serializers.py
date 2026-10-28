# AI contribution: 50% or more AI-generated
"""HTTP types only; posting decisions belong to the service/domain."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.listings.models import Listing
from modules.stores import queries as store_queries


class AwareDateTimeField(serializers.DateTimeField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(default_timezone=UTC, **kwargs)

    def to_internal_value(self, data: Any) -> datetime:
        parsed = data if isinstance(data, datetime) else None
        if isinstance(data, str):
            try:
                parsed = parse_datetime(data)
            except ValueError:
                pass  # Let DRF report its ordinary invalid-format message.
        if parsed is not None and parsed.utcoffset() is None:
            raise serializers.ValidationError(
                _("Include a timezone offset in the pickup time.")
            )
        return super().to_internal_value(data)


@extend_schema_field(OpenApiTypes.BINARY)
class PhotoUploadField(serializers.FileField):
    """Document a multipart upload, rather than an existing file's URL."""


class NewListingSerializer(serializers.Serializer):
    category = serializers.UUIDField()
    store = serializers.UUIDField(required=False)
    title = serializers.CharField()
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    quantity = serializers.IntegerField(default=1)
    unit = serializers.CharField(default="item")
    max_per_household = serializers.IntegerField(default=1)
    pickup_start = AwareDateTimeField()
    pickup_end = AwareDateTimeField()
    best_before = serializers.DateField(required=False, allow_null=True)
    estimated_value_cents = serializers.IntegerField(required=False, allow_null=True)
    safe_and_allowed = serializers.BooleanField()
    photo = PhotoUploadField(required=False, allow_null=True)

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {
                        key: _("This field cannot be submitted.")
                        for key in sorted(unknown)
                    }
                )
        return super().to_internal_value(data)


class StoreAddressSerializer(serializers.Serializer):
    street_number = serializers.CharField()
    street_name = serializers.CharField()
    unit = serializers.CharField(allow_null=True)
    city = serializers.CharField()
    postal_code = serializers.CharField()


class PostedListingSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField(source="quantity_total")
    store = serializers.UUIDField(source="store_id")
    category = serializers.UUIDField(source="category_id")
    pickup_start = AwareDateTimeField()
    pickup_end = AwareDateTimeField()
    published_at = AwareDateTimeField()
    safe_confirmed_at = AwareDateTimeField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id",
            "store",
            "category",
            "title",
            "description",
            "quantity",
            "quantity_reserved",
            "unit",
            "max_per_household",
            "pickup_start",
            "pickup_end",
            "best_before",
            "estimated_value_cents",
            "status",
            "safe_confirmed_at",
            "published_at",
            "location",
        )
        read_only_fields = fields

    @extend_schema_field(StoreAddressSerializer)
    def get_location(self, listing: Listing) -> dict[str, Any] | None:
        return store_queries.address(listing.store_id)


class PostingErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
