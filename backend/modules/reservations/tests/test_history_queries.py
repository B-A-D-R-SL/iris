# AI contribution: 50% or more AI-generated
"""The order and contents of a household's pickup history (US-48, BR-RES-012).

Upcoming means ``reserved`` with the pickup window not ended, the end included.
Upcoming reservations come first, soonest first; then every other one, latest
pickup window first. Codes are only kept while upcoming.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from modules.reservations import queries
from modules.reservations.models import ReservationStatus
from modules.reservations.tests.factories import (
    ReservationFactory,
    approved_household,
    open_listing,
)

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 25, 20, tzinfo=UTC)


@pytest.fixture
def household() -> Any:
    """An approved household to hold the reservations."""
    return approved_household(NOW)


def _reserve(
    household: Any,
    title: str,
    *,
    starts_in: timedelta,
    lasts: timedelta = timedelta(hours=2),
    **kwargs: Any,
) -> Any:
    """A reservation on a listing ``title`` whose pickup starts at NOW + ``starts_in``."""
    start = NOW + starts_in
    listing = open_listing(
        NOW, pickup_start=start, pickup_end=start + lasts, title=title
    )
    return ReservationFactory(
        listing=listing, household=household, made_by=household.holder, **kwargs
    )


def _history(household_id: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Every history entry of the household at NOW, as the API pages them."""
    return queries.history_entries(
        queries.household_history(household_id, now=NOW, **kwargs)
    )


# rule: BR-RES-012
def test_upcoming_soonest_first_then_past_latest_first(household: Any) -> None:
    """Upcoming ones lead, soonest first; the rest follow, latest window first."""
    _reserve(
        household, "Past, last week", starts_in=-timedelta(days=7), status="picked_up"
    )
    _reserve(household, "Upcoming, tomorrow", starts_in=timedelta(days=1))
    _reserve(
        household, "Past, yesterday", starts_in=-timedelta(days=1), status="no_show"
    )
    _reserve(household, "Upcoming, open now", starts_in=-timedelta(hours=1))
    # Cancelled before its window: past, although the window is still ahead.
    _reserve(
        household,
        "Cancelled, next week",
        starts_in=timedelta(days=7),
        status="cancelled",
    )

    entries = _history(household.pk)

    assert [(entry["title"], entry["upcoming"]) for entry in entries] == [
        ("Upcoming, open now", True),
        ("Upcoming, tomorrow", True),
        ("Cancelled, next week", False),
        ("Past, yesterday", False),
        ("Past, last week", False),
    ]


# rule: BR-RES-012
def test_window_end_is_included_then_the_reservation_is_past(household: Any) -> None:
    """At the window's end it is still upcoming; a minute after, it has no code."""
    ends_now = _reserve(household, "Ends now", starts_in=-timedelta(hours=2))
    ended = _reserve(
        household,
        "Ended a minute ago",
        starts_in=-timedelta(hours=2),
        lasts=timedelta(hours=2) - timedelta(minutes=1),
    )

    entries = {entry["id"]: entry for entry in _history(household.pk)}

    assert entries[ends_now.pk]["upcoming"] is True
    assert entries[ends_now.pk]["pickup_code"] == ends_now.pickup_code
    # Still saved as reserved (no-shows are not closed yet, US-46), but its code
    # can no longer be used: it is past and has no code.
    assert entries[ended.pk]["status"] == ReservationStatus.RESERVED
    assert entries[ended.pk]["upcoming"] is False
    assert entries[ended.pk]["pickup_code"] is None


# rule: BR-RES-012
def test_as_of_keeps_the_order_while_upcoming_follows_now(household: Any) -> None:
    """Rows are listed as at ``as_of``; ``upcoming`` and the code are at ``now``."""
    _reserve(household, "Ended an hour ago", starts_in=-timedelta(hours=3))
    _reserve(
        household,
        "Picked up today",
        starts_in=-timedelta(minutes=30),
        status="picked_up",
    )

    entries = queries.history_entries(
        queries.household_history(household.pk, now=NOW, as_of=NOW - timedelta(hours=2))
    )

    # Upcoming two hours ago, so still listed first, but no longer upcoming.
    assert [
        (entry["title"], entry["upcoming"], entry["pickup_code"]) for entry in entries
    ] == [("Ended an hour ago", False, None), ("Picked up today", False, None)]


def test_same_window_is_ordered_by_id(household: Any) -> None:
    """Two reservations on one listing keep a stable order, so pages never repeat."""
    first = _reserve(household, "A", starts_in=-timedelta(days=2), status="picked_up")
    second: Any = ReservationFactory(
        listing=first.listing,
        household=household,
        made_by=household.holder,
        status="cancelled",
    )

    entries = _history(household.pk)

    assert [entry["id"] for entry in entries] == sorted([first.pk, second.pk])


def test_entries_carry_the_listing_and_its_store(household: Any) -> None:
    """Each entry has the listing's title, unit and window and its store's name."""
    reservation = _reserve(household, "Couches taille 4", starts_in=timedelta(days=1))

    (entry,) = _history(household.pk)

    listing = reservation.listing
    assert entry["id"] == reservation.pk
    assert entry["listing_id"] == listing.pk
    assert entry["title"] == "Couches taille 4"
    assert entry["unit"] == listing.unit
    assert entry["store_id"] == listing.store_id
    assert entry["store_name"] == listing.store.name
    assert entry["pickup_start"] == listing.pickup_start
    assert entry["pickup_end"] == listing.pickup_end


def test_status_filter(household: Any) -> None:
    """A status filter keeps that status only."""
    _reserve(household, "Kept", starts_in=-timedelta(days=1), status="no_show")
    _reserve(household, "Left out", starts_in=timedelta(days=1))

    entries = _history(household.pk, status="no_show")

    assert [entry["title"] for entry in entries] == ["Kept"]


# rule: BR-RES-011
def test_no_household_has_no_history(household: Any) -> None:
    """None (no household) gives no rows, even when other households have some."""
    _reserve(household, "Someone else's", starts_in=timedelta(days=1))

    assert _history(None) == []


def test_empty_page_gives_no_entries() -> None:
    """An empty page stays empty."""
    assert queries.history_entries([]) == []
