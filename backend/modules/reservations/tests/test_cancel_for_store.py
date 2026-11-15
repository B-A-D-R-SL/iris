# AI contribution: 50% or more AI-generated
"""Reservations on listings of a deactivated store (US-14)."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from django.db import transaction

from modules.households.queries import email_contacts
from modules.households.tests.factories import HouseholdFactory
from modules.listings.tests.factories import ListingFactory
from modules.reservations import services
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.queries import household_count_for_listings
from modules.reservations.tests.factories import ReservationFactory

pytestmark = pytest.mark.django_db


def _reservation(**values: Any) -> Reservation:
    return cast(Reservation, ReservationFactory(**values))


NOW = datetime(2026, 11, 14, 15, tzinfo=UTC)
STORE_NAME = "Épicerie Démo du Quartier"


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, str, dict[str, Any]]]:
    """Capture queued emails instead of creating email jobs."""
    calls: list[tuple[Any, str, dict[str, Any]]] = []
    monkeypatch.setattr(
        services.notification_services,
        "send",
        lambda to, key, context: calls.append((to, key, dict(context))),
    )
    return calls


def _listing(**kwargs: Any) -> Any:
    start = NOW + timedelta(hours=1)
    return ListingFactory(
        pickup_start=start, pickup_end=start + timedelta(hours=2), **kwargs
    )


def _household(email: str | None = None, language: str = "fr") -> Any:
    return HouseholdFactory(email=email, preferred_language=language)


def _cancel(listing_ids: list[Any]) -> int:
    with transaction.atomic():
        return services.cancel_for_cancelled_listings(
            listing_ids, store_name=STORE_NAME
        )


# rule: BR-STORE-003
def test_reserved_claims_become_cancelled_by_store_without_a_strike(sent) -> None:
    listing = _listing(title="Bread bundle", quantity_reserved=3)
    reservation = _reservation(
        listing=listing, household=_household("a@example.test", "en"), quantity=3
    )

    assert _cancel([listing.pk]) == 1

    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.CANCELLED_BY_STORE
    assert reservation.late_cancel is False
    listing.refresh_from_db()
    assert listing.quantity_reserved == 3  # units are not given back
    assert sent == [
        (
            "a@example.test",
            "reservation_cancelled_by_store",
            {
                "language": "en",
                "store_name": STORE_NAME,
                "listing_title": "Bread bundle",
                "quantity": "3",
            },
        )
    ]


# rule: BR-STORE-003
def test_one_email_per_reservation_even_for_the_same_household(sent) -> None:
    household = _household("same@example.test")
    first, second = _listing(), _listing()
    _reservation(listing=first, household=household)
    _reservation(listing=second, household=household)

    assert _cancel([first.pk, second.pk]) == 2
    assert len(sent) == 2
    assert {call[2]["listing_title"] for call in sent} == {first.title, second.title}


# rule: BR-STORE-003
def test_household_without_email_is_cancelled_but_not_emailed(sent) -> None:
    listing = _listing()
    reservation = _reservation(listing=listing, household=_household(None))

    assert _cancel([listing.pk]) == 1

    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.CANCELLED_BY_STORE
    assert sent == []


def test_only_reserved_claims_on_the_given_listings_change(sent) -> None:
    listing, other = _listing(), _listing()
    picked_up = _reservation(
        listing=listing, status=ReservationStatus.PICKED_UP, picked_up_at=NOW
    )
    elsewhere = _reservation(listing=other)

    assert _cancel([listing.pk]) == 0

    picked_up.refresh_from_db()
    elsewhere.refresh_from_db()
    assert picked_up.status == ReservationStatus.PICKED_UP
    assert elsewhere.status == ReservationStatus.RESERVED
    assert sent == []


@pytest.mark.django_db(transaction=True)
def test_requires_a_transaction() -> None:
    with pytest.raises(RuntimeError):
        services.cancel_for_cancelled_listings([], store_name=STORE_NAME)


# rule: BR-STORE-003
def test_household_count_counts_each_emailed_household_once() -> None:
    """The preview counts who gets an email: once per household, never without email."""
    household = _household("twice@example.test")
    first, second = _listing(), _listing()
    _reservation(listing=first, household=household)
    _reservation(listing=second, household=household)
    _reservation(listing=second, household=_household("other@example.test"))
    _reservation(listing=second, household=_household(None))
    _reservation(
        listing=first,
        household=_household("cancelled@example.test"),
        status=ReservationStatus.CANCELLED,
    )

    assert household_count_for_listings([first.pk, second.pk]) == 2
    assert household_count_for_listings([]) == 0


def test_email_contacts_gives_address_and_language() -> None:
    online = _household("x@example.test", "en")
    walk_in = _household(None)

    assert email_contacts([online.pk, walk_in.pk]) == {
        online.pk: ("x@example.test", "en"),
        walk_in.pk: (None, "fr"),
    }
