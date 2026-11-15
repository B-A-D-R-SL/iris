# AI contribution: 50% or more AI-generated
"""Admin store screens (US-14): list, detail, edit and status changes.

Formats are checked by the stores service and the Store model, so the
messages match everywhere a store is saved; these serializers give the shape
and the OpenAPI types.
"""

from datetime import UTC
from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from modules.stores.models import Store
from modules.stores.services import EDITABLE_STORE_FIELDS, can_change_status


class DayHoursSerializer(serializers.Serializer):
    """One opening range, as "HH:MM" local times."""

    open = serializers.CharField()
    close = serializers.CharField()


class OpeningHoursSerializer(serializers.Serializer):
    """Each day is a range, or null when closed. ``notes`` is read-only text
    copied from the partner application, shown until the grid replaces it."""

    mon = DayHoursSerializer(allow_null=True)
    tue = DayHoursSerializer(allow_null=True)
    wed = DayHoursSerializer(allow_null=True)
    thu = DayHoursSerializer(allow_null=True)
    fri = DayHoursSerializer(allow_null=True)
    sat = DayHoursSerializer(allow_null=True)
    sun = DayHoursSerializer(allow_null=True)
    notes = serializers.CharField(read_only=True, allow_null=True)


class StaffStoreListItemSerializer(serializers.ModelSerializer):
    """One row of the admin store list (W7.1)."""

    open_listings = serializers.SerializerMethodField()

    def get_open_listings(self, store: Store) -> int:
        return int(self.context.get("open_listings", {}).get(store.pk, 0))

    class Meta:
        model = Store
        fields = (
            "id",
            "name",
            "street_number",
            "street_name",
            "unit",
            "city",
            "postal_code",
            "is_active",
            "is_badr",
            "open_listings",
        )
        read_only_fields = fields


class StoreCountsSerializer(serializers.Serializer):
    all = serializers.IntegerField()
    active = serializers.IntegerField()
    inactive = serializers.IntegerField()


class StaffStorePageSerializer(serializers.Serializer):
    """Team paging envelope plus the counts for the status chips."""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = StaffStoreListItemSerializer(many=True)
    counts = StoreCountsSerializer()


class StaffStoreSerializer(serializers.ModelSerializer):
    """A store as the admin edits it (W7.2), with the deactivation preview."""

    opening_hours = OpeningHoursSerializer()
    created_at = serializers.DateTimeField(default_timezone=UTC)
    updated_at = serializers.DateTimeField(default_timezone=UTC)
    open_listings = serializers.SerializerMethodField()
    households_to_notify = serializers.SerializerMethodField()
    can_change_status = serializers.SerializerMethodField()

    def get_open_listings(self, store: Store) -> int:
        return int(self.context.get("preview", {}).get("open_listings", 0))

    def get_households_to_notify(self, store: Store) -> int:
        return int(self.context.get("preview", {}).get("households_to_notify", 0))

    def get_can_change_status(self, store: Store) -> bool:
        """Whether the admin may deactivate or reactivate it (not B.A.D.R.)."""
        return can_change_status(store)

    class Meta:
        model = Store
        fields: tuple[str, ...] = (
            "id",
            "name",
            "street_number",
            "street_name",
            "unit",
            "city",
            "postal_code",
            "phone",
            "email",
            "opening_hours",
            "pickup_instructions",
            "is_badr",
            "is_active",
            "created_at",
            "updated_at",
            "open_listings",
            "households_to_notify",
            "can_change_status",
        )
        read_only_fields: tuple[str, ...] = fields


class StoreDeactivatedSerializer(StaffStoreSerializer):
    """The deactivated store and what the deactivation cancelled."""

    listings_cancelled = serializers.IntegerField(read_only=True)
    reservations_cancelled = serializers.IntegerField(read_only=True)

    class Meta(StaffStoreSerializer.Meta):
        fields = (
            *StaffStoreSerializer.Meta.fields,
            "listings_cancelled",
            "reservations_cancelled",
        )
        read_only_fields = fields


class StaffStoreUpdateSerializer(serializers.Serializer):
    """PATCH body: any editable field; anything else is refused."""

    name = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False
    )
    street_number = serializers.CharField(required=False, allow_blank=True)
    street_name = serializers.CharField(required=False, allow_blank=True)
    unit = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.CharField(required=False, allow_blank=True)
    opening_hours = OpeningHoursSerializer(required=False)
    pickup_instructions = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Refuse read-only or unknown keys instead of ignoring them."""
        unknown = sorted(set(self.initial_data) - EDITABLE_STORE_FIELDS)
        if unknown:
            raise serializers.ValidationError(
                {field: [_("This field cannot be changed.")] for field in unknown}
            )
        return attrs


class StoreStatusChangeSerializer(serializers.Serializer):
    """Deactivation or reactivation body; the service checks the reason."""

    reason = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
        error_messages={"required": _("Enter a reason.")},
    )


class StaffStoreFilterSerializer(serializers.Serializer):
    """Query string of the store list."""

    q = serializers.CharField(required=False, allow_blank=True, max_length=150)
    status = serializers.ChoiceField(
        choices=("active", "inactive"),
        required=False,
        error_messages={"invalid_choice": _("Choose active or inactive.")},
    )
