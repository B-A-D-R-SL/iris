# AI contribution: 50% or more AI-generated
"""Simultaneous reservations (US-41) against a real PostgreSQL database.

Each thread has its own database connection and its own transaction, as two
phones would. ``transaction=True`` makes the test data really committed, so
the threads can see it; ordinary tests keep everything in one uncommitted
transaction that other connections cannot see. A barrier releases all the
threads at once.
"""

import threading
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.db import connection

from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.services import (
    QUANTITY_OVER_LISTING_LIMIT,
    SOLD_OUT,
    TOO_MANY_ACTIVE_RESERVATIONS,
    ReservationRefused,
    reserve,
)
from modules.reservations.tests.factories import (
    ReservationFactory,
    approved_household,
    open_listing,
    publish_reservation_rules,
)

pytestmark = pytest.mark.django_db(transaction=True)

NOW = datetime(2026, 11, 9, 15, tzinfo=UTC)
RESERVED = "reserved"


def _run_together(calls: list[Callable[[], Any]]) -> Counter[str]:
    """Start every call at the same moment; count the outcomes."""
    barrier = threading.Barrier(len(calls), timeout=30)

    def run(call: Callable[[], Any]) -> str:
        try:
            barrier.wait()
            call()
            return RESERVED
        except ReservationRefused as refused:
            return refused.code
        finally:
            connection.close()  # this thread's own connection

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        return Counter(pool.map(run, calls))


def _reserve_call(household: Any, listing: Any, quantity: int = 1) -> Callable[[], Any]:
    return lambda: reserve(
        household.holder, household.pk, listing.pk, quantity, now=NOW
    )


@pytest.fixture(autouse=True)
def rules() -> None:
    publish_reservation_rules(NOW - timedelta(days=1))


# rule: BR-RES-009 acceptance criterion 1 (#516: 20 requests for 5 units).
def test_twenty_households_at_once_get_exactly_five_units() -> None:
    listing = open_listing(NOW, quantity_total=5, max_per_household=1)
    households = [approved_household(NOW) for _ in range(20)]

    outcomes = _run_together([_reserve_call(h, listing) for h in households])

    assert outcomes == Counter({RESERVED: 5, SOLD_OUT: 15})
    listing.refresh_from_db()
    assert listing.quantity_reserved == 5
    assert Reservation.objects.filter(listing=listing).count() == 5


# rule: BR-RES-008 two phones of one household cannot pass the limit together.
def test_two_phones_cannot_make_a_fourth_active_reservation() -> None:
    household = approved_household(NOW)
    for _ in range(2):
        ReservationFactory(household=household, made_by=household.holder)
    listings = [open_listing(NOW) for _ in range(2)]

    outcomes = _run_together([_reserve_call(household, item) for item in listings])

    assert outcomes == Counter({RESERVED: 1, TOO_MANY_ACTIVE_RESERVATIONS: 1})
    active = Reservation.objects.filter(
        household=household, status=ReservationStatus.RESERVED
    )
    assert active.count() == 3


# rule: BR-RES-007 two phones cannot pass the listing max together.
def test_two_phones_cannot_pass_the_listing_max_together() -> None:
    household = approved_household(NOW)
    listing = open_listing(NOW, quantity_total=10, max_per_household=2)

    outcomes = _run_together([_reserve_call(household, listing, 2) for _ in range(2)])

    assert outcomes == Counter({RESERVED: 1, QUANTITY_OVER_LISTING_LIMIT: 1})
    listing.refresh_from_db()
    assert listing.quantity_reserved == 2
