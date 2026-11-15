# AI contribution: 50% or more AI-generated
"""Store deactivation and household suspension on the same reservation at once.

Both cancel reservations and touch listings. Store deactivation (US-14) locks
the listings, then the reservations; household suspension (US-32) must take
them in the same order, or each transaction waits for the other until
PostgreSQL aborts one as a deadlock (review of PR #710).

The test forces that interleaving with two threads on real connections
(``transaction=True``): the deactivation side locks the listing first, waits
until the suspension is blocked on a lock, then goes on to the reservation.
"""

import threading
from datetime import timedelta
from typing import Any, cast

import pytest
from django.db import connection, transaction
from django.utils import timezone

from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory
from modules.listings.models import Listing
from modules.listings.services import cancel_all_for_store
from modules.listings.tests.factories import ListingFactory
from modules.reservations import services
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.tests.factories import ReservationFactory

pytestmark = pytest.mark.django_db(transaction=True)

POLL = threading.Event()  # never set: its wait() is the pause between checks


def _wait_until_another_session_waits_for_a_lock() -> None:
    """Return once PostgreSQL shows a transaction waiting on a row lock."""
    for _ in range(500):  # at most about 10 seconds
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_locks WHERE NOT granted LIMIT 1")
            if cursor.fetchone():
                return
        POLL.wait(0.02)
    raise AssertionError("The suspension never waited for a lock.")


def _run(name: str, call: Any, errors: dict[str, BaseException]) -> threading.Thread:
    def target() -> None:
        try:
            call()
        except BaseException as error:  # noqa: BLE001 - reported by the test
            errors[name] = error
        finally:
            connection.close()  # this thread's own connection

    thread = threading.Thread(target=target, name=name)
    thread.start()
    return thread


# rule: BR-STORE-003
# rule: BR-HH-SUSPEND-002
def test_deactivation_and_suspension_on_one_reservation_do_not_deadlock() -> None:
    start = timezone.now() + timedelta(hours=2)
    listing = cast(
        Listing,
        ListingFactory(
            pickup_start=start,
            pickup_end=start + timedelta(hours=2),
            quantity_total=5,
            quantity_reserved=2,
        ),
    )
    household = cast(Household, HouseholdFactory(email=None))  # no email job
    reservation = cast(
        Reservation,
        ReservationFactory(listing=listing, household=household, quantity=2),
    )
    listing_locked = threading.Event()
    suspension_started = threading.Event()
    errors: dict[str, BaseException] = {}

    def deactivate() -> None:
        with transaction.atomic():
            listing_ids = cancel_all_for_store(listing.store_id, now=timezone.now())
            listing_locked.set()
            assert suspension_started.wait(10)
            _wait_until_another_session_waits_for_a_lock()
            services.cancel_for_cancelled_listings(listing_ids, store_name="Demo")

    def suspend() -> None:
        assert listing_locked.wait(10)
        suspension_started.set()
        with transaction.atomic():
            services.cancel_open_for_household(household.pk)

    threads = [
        _run("deactivate", deactivate, errors),
        _run("suspend", suspend, errors),
    ]
    for thread in threads:
        thread.join(30)

    assert errors == {}
    reservation.refresh_from_db()
    listing.refresh_from_db()
    # The deactivation held the listing first, so it cancelled the claim; the
    # suspension then found nothing left to cancel and gave no units back.
    assert reservation.status == ReservationStatus.CANCELLED_BY_STORE
    assert listing.quantity_reserved == 2
