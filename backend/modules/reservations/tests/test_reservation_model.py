# AI contribution: 50% or more AI-generated
"""The reservation table (US-41, #515): constraints, timestamps and factory."""

from typing import cast

import pytest
from django.db import IntegrityError, transaction

from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.tests.factories import ReservationFactory

pytestmark = pytest.mark.django_db


def test_factory_makes_a_live_reservation_with_timestamps() -> None:
    reservation = cast(Reservation, ReservationFactory())
    assert reservation.status == ReservationStatus.RESERVED
    assert reservation.created_at is not None
    assert reservation.updated_at >= reservation.created_at


# rule: BR-RES-010 unique per listing.
def test_same_code_twice_on_one_listing_is_refused() -> None:
    first = cast(Reservation, ReservationFactory())
    with pytest.raises(IntegrityError), transaction.atomic():
        ReservationFactory(listing=first.listing, pickup_code=first.pickup_code)


def test_same_code_on_two_listings_is_allowed() -> None:
    first = cast(Reservation, ReservationFactory())
    second = cast(Reservation, ReservationFactory(pickup_code=first.pickup_code))
    assert second.listing_id != first.listing_id


def test_quantity_below_one_is_refused() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        ReservationFactory(quantity=0)


def test_unknown_status_is_refused() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        ReservationFactory(status="waiting")
