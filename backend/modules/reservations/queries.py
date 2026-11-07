# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for reservations: the pickup lookup (US-44)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from modules.households import queries as household_queries
from modules.listings import queries as listing_queries
from modules.reservations.domain import pickup
from modules.reservations.domain.pickup import PickupRefused
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.permissions import pickup_store_id

STATUS_REFUSALS = {
    ReservationStatus.PICKED_UP: pickup.ALREADY_PICKED_UP,
    ReservationStatus.CANCELLED: pickup.CANCELLED,
    ReservationStatus.CANCELLED_BY_STORE: pickup.CANCELLED,
    ReservationStatus.NO_SHOW: pickup.NO_SHOW,
}


@dataclass(frozen=True)
class Pickup:
    """What staff see before handing over the goods: no contact details."""

    id: UUID
    status: str
    holder: str | None
    alternate: str | None
    title: str
    unit: str
    quantity: int
    pickup_code: str
    pickup_start: datetime
    pickup_end: datetime
    picked_up_at: datetime | None


def lookup_pickup(staff: Any, code: str, *, now: datetime) -> Pickup:
    """Find the reservation ``code`` names at the staff member's store.

    Codes are unique per listing, not per store (BR-RES-004). One reserved match
    is the answer. Several reserved matches are refused rather than guessed.
    With no reserved match, the latest match explains why the code cannot be
    used. Raises PickupRefused for every case staff must not act on.
    """
    listings = listing_queries.pickup_listings(pickup_store_id(staff))
    matches = list(
        Reservation.objects.filter(
            pickup_code=code, listing_id__in=listings.values("id")
        )
    )
    if not matches:
        raise PickupRefused(_missing_code_reason(code, listings))
    rows = {
        row["id"]: row
        for row in listings.filter(id__in={match.listing_id for match in matches})
    }
    reservation = _single_match(matches, rows)
    return confirmable_pickup(reservation, rows[reservation.listing_id], now=now)


def confirmable_pickup(
    reservation: Reservation, listing: dict[str, Any], *, now: datetime
) -> Pickup:
    """The pickup if it can be confirmed now (BR-RES-002); raises PickupRefused if not."""
    refusal = STATUS_REFUSALS.get(ReservationStatus(reservation.status))
    if refusal is not None:
        raise PickupRefused(refusal, picked_up_at=reservation.picked_up_at)
    refusal = pickup.window_refusal(now, listing["pickup_start"], listing["pickup_end"])
    if refusal is not None:
        raise PickupRefused(refusal)
    return describe_pickup(reservation, listing)


def describe_pickup(reservation: Reservation, listing: dict[str, Any]) -> Pickup:
    """Combine the reservation, its listing and the names staff may see."""
    names = household_queries.pickup_names(reservation.household_id)
    if names is None:
        raise PickupRefused(pickup.UNKNOWN_CODE)
    return Pickup(
        id=reservation.pk,
        status=reservation.status,
        holder=names["holder"],
        alternate=names["alternate"],
        title=listing["title"],
        unit=listing["unit"],
        quantity=reservation.quantity,
        pickup_code=reservation.pickup_code,
        pickup_start=listing["pickup_start"],
        pickup_end=listing["pickup_end"],
        picked_up_at=reservation.picked_up_at,
    )


def _missing_code_reason(code: str, listings: QuerySet[Any, dict[str, Any]]) -> str:
    """A live reservation at another store says so; anything else is unknown.

    The answer names no store and no household, so staff only redirect the person.
    """
    elsewhere = (
        Reservation.objects.filter(pickup_code=code, status=ReservationStatus.RESERVED)
        .exclude(listing_id__in=listings.values("id"))
        .exists()
    )
    return pickup.WRONG_STORE if elsewhere else pickup.UNKNOWN_CODE


def _single_match(
    matches: list[Reservation], rows: dict[UUID, dict[str, Any]]
) -> Reservation:
    """The one reserved match, or the latest match to explain a refusal."""
    reserved = [
        match for match in matches if match.status == ReservationStatus.RESERVED
    ]
    if len(reserved) > 1:
        raise PickupRefused(pickup.AMBIGUOUS_CODE)
    if reserved:
        return reserved[0]
    return max(matches, key=lambda match: rows[match.listing_id]["pickup_end"])
