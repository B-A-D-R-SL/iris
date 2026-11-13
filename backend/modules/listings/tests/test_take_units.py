# AI contribution: 50% or more AI-generated
"""take_units and reservable_listing (US-41): stock only moves when it can."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.db import transaction
from django.utils import timezone

from modules.listings.models import ListingStatus
from modules.listings.queries import reservable_listing
from modules.listings.services import take_units
from modules.listings.tests.factories import ListingFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 9, 15, tzinfo=UTC)
HOUSEHOLD = uuid.uuid4()  # reservable_listing only needs an approved household's ID


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timezone, "now", lambda: NOW)


def _listing(**kwargs: Any) -> Any:
    start = NOW + timedelta(hours=1)
    values = {
        "quantity_total": 5,
        "pickup_start": start,
        "pickup_end": start + timedelta(hours=2),
    }
    return ListingFactory(**(values | kwargs))


def _take(listing: Any, quantity: int, now: datetime = NOW) -> bool:
    with transaction.atomic():
        return take_units(listing.pk, quantity, now=now)


# rule: BR-RES-009
def test_takes_units_when_enough_are_left() -> None:
    listing = _listing(quantity_reserved=3)
    assert _take(listing, 2) is True
    listing.refresh_from_db()
    assert listing.quantity_reserved == 5


# rule: BR-RES-009
@pytest.mark.parametrize(
    ("changes", "quantity"),
    [
        ({"quantity_reserved": 5}, 1),  # sold out
        ({"quantity_reserved": 4}, 2),  # one left, two asked
        ({"status": ListingStatus.CLOSED}, 1),
        ({"status": ListingStatus.CANCELLED}, 1),
    ],
)
def test_refuses_and_changes_nothing(changes: dict[str, Any], quantity: int) -> None:
    listing = _listing(**changes)
    before = listing.quantity_reserved
    assert _take(listing, quantity) is False
    listing.refresh_from_db()
    assert listing.quantity_reserved == before


# rule: BR-RES-009 not after the pickup has ended.
def test_refuses_after_the_pickup_ends() -> None:
    listing = _listing()
    assert _take(listing, 1, now=listing.pickup_end) is False
    assert _take(listing, 1, now=listing.pickup_end - timedelta(seconds=1)) is True


def test_refuses_an_unknown_listing() -> None:
    with transaction.atomic():
        assert take_units(uuid.uuid4(), 1, now=NOW) is False


# Ordinary tests already run inside a transaction, so this one must not.
@pytest.mark.django_db(transaction=True)
def test_must_run_inside_a_transaction() -> None:
    listing = _listing()
    with pytest.raises(RuntimeError, match="transaction"):
        take_units(listing.pk, 1, now=NOW)


@pytest.mark.parametrize("quantity", [0, -1])
def test_refuses_a_quantity_below_one(quantity: int) -> None:
    listing = _listing()
    with pytest.raises(ValueError), transaction.atomic():
        take_units(listing.pk, quantity, now=NOW)


def test_reservable_listing_gives_the_limits() -> None:
    listing = _listing(quantity_reserved=1, max_per_household=2)
    assert reservable_listing(HOUSEHOLD, listing.pk, NOW) == {
        "id": listing.pk,
        "max_per_household": 2,
        "units_left": 4,
    }


def test_reservable_listing_says_sold_out_with_zero_units() -> None:
    listing = _listing(quantity_reserved=5)
    found = reservable_listing(HOUSEHOLD, listing.pk, NOW)
    assert found is not None
    assert found["units_left"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"status": ListingStatus.CLOSED},
        {"status": ListingStatus.CANCELLED},
        {"pickup_start": NOW - timedelta(hours=3), "pickup_end": NOW},
    ],
)
def test_reservable_listing_hides_what_cannot_be_reserved(
    changes: dict[str, Any],
) -> None:
    listing = _listing(**changes)
    assert reservable_listing(HOUSEHOLD, listing.pk, NOW) is None


def test_reservable_listing_needs_an_approved_household() -> None:
    listing = _listing(quantity_reserved=5)
    assert reservable_listing(None, listing.pk, NOW) is None
