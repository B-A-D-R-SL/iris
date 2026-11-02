# AI contribution: 50% or more AI-generated
"""Database rules of the Listing model (T-05.33.2)."""

from datetime import timedelta
from typing import Any, cast

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import F, ProtectedError

from modules.listings.models import Listing
from modules.listings.tests.factories import ListingFactory

ONE_HOUR = timedelta(hours=1)


@pytest.mark.django_db
def test_factory_builds_a_valid_published_listing() -> None:
    listing = cast(Listing, ListingFactory())

    listing.full_clean()
    assert listing.status == "published"
    assert listing.quantity_reserved == 0
    assert listing.unit == "item"
    assert listing.max_per_household == 1
    assert listing.safe_confirmed_by == listing.created_by
    assert listing.cancelled_at is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"quantity_total": 1}, id="smallest quantity"),
        pytest.param({"quantity_total": 999}, id="largest quantity"),
        pytest.param(
            {"quantity_total": 5, "quantity_reserved": 5}, id="fully reserved"
        ),
        pytest.param({"max_per_household": 10}, id="largest household limit"),
        pytest.param({"estimated_value_cents": 0}, id="free value"),
        pytest.param({"estimated_value_cents": 100_000}, id="largest value"),
        pytest.param({"unit": "bundle"}, id="bundle unit"),
        pytest.param({"status": "cancelled"}, id="cancelled status"),
    ],
)
def test_boundary_values_are_accepted(overrides: dict[str, Any]) -> None:
    listing = cast(Listing, ListingFactory(**overrides))

    listing.refresh_from_db()
    for field, value in overrides.items():
        assert getattr(listing, field) == value


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        pytest.param(
            {"quantity_total": 0}, "listings_quantity_total_range", id="no units"
        ),
        pytest.param(
            {"quantity_total": 1000},
            "listings_quantity_total_range",
            id="too many units",
        ),
        pytest.param(
            {"quantity_reserved": -1},
            "listings_quantity_reserved_within_total",
            id="negative reserved",
        ),
        pytest.param(
            {"quantity_total": 5, "quantity_reserved": 6},
            "listings_quantity_reserved_within_total",
            id="reserved above total",
        ),
        pytest.param(
            {"max_per_household": 0},
            "listings_max_per_household_range",
            id="household limit zero",
        ),
        pytest.param(
            {"max_per_household": 11},
            "listings_max_per_household_range",
            id="household limit too high",
        ),
        pytest.param(
            {"pickup_end": F("pickup_start")},
            "listings_pickup_end_after_start",
            id="empty pickup window",
        ),
        pytest.param(
            {"pickup_end": F("pickup_start") - ONE_HOUR},
            "listings_pickup_end_after_start",
            id="pickup ends before it starts",
        ),
        pytest.param(
            {"estimated_value_cents": -1},
            "listings_estimated_value_cents_range",
            id="negative value",
        ),
        pytest.param(
            {"estimated_value_cents": 100_001},
            "listings_estimated_value_cents_range",
            id="value above $1,000",
        ),
        pytest.param({"unit": "box"}, "listings_unit_valid", id="unknown unit"),
        pytest.param({"status": "draft"}, "listings_status_valid", id="unknown status"),
    ],
)
def test_database_rejects_invalid_values(
    overrides: dict[str, Any], constraint: str
) -> None:
    listing = cast(Listing, ListingFactory())

    with pytest.raises(IntegrityError, match=constraint):
        Listing.objects.filter(pk=listing.pk).update(**overrides)


@pytest.mark.django_db
def test_database_rejects_reserving_more_units_than_left() -> None:
    listing = cast(Listing, ListingFactory(quantity_total=3, quantity_reserved=2))

    with pytest.raises(IntegrityError, match="listings_quantity_reserved_within_total"):
        Listing.objects.filter(pk=listing.pk).update(
            quantity_reserved=F("quantity_reserved") + 2
        )


@pytest.mark.django_db
def test_full_clean_rejects_a_one_character_title() -> None:
    listing = cast(Listing, ListingFactory())
    listing.title = "A"

    with pytest.raises(ValidationError) as error:
        listing.full_clean()
    assert "title" in error.value.message_dict


@pytest.mark.django_db
def test_category_and_store_in_use_cannot_be_deleted() -> None:
    listing = cast(Listing, ListingFactory())

    with pytest.raises(ProtectedError):
        listing.category.delete()
    with pytest.raises(ProtectedError):
        listing.store.delete()
