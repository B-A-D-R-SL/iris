# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for reservations.

The pickup lookup (US-44) and a household's pickup history (US-48).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import (
    BooleanField,
    Case,
    DateTimeField,
    F,
    OuterRef,
    QuerySet,
    Value,
    When,
)

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
    # A finished local row must not hide a live claim at another store (BR-RES-004).
    if (
        reservation.status != ReservationStatus.RESERVED
        and _missing_code_reason(code, listings) == pickup.WRONG_STORE
    ):
        raise PickupRefused(pickup.WRONG_STORE)
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
    Anonymized households stay unknown (BR-RES-003).
    """
    elsewhere = Reservation.objects.filter(
        pickup_code=code, status=ReservationStatus.RESERVED
    ).exclude(listing_id__in=listings.values("id"))
    if household_queries.any_visible_for_pickup(
        elsewhere.values_list("household_id", flat=True)
    ):
        return pickup.WRONG_STORE
    return pickup.UNKNOWN_CODE


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


def household_count_for_listings(listing_ids: list[UUID]) -> int:
    """Households that would be emailed if these listings were cancelled (US-14).

    Only households with a reserved claim and an email address count, matching
    who ``cancel_for_cancelled_listings`` actually emails.
    """
    household_ids = set(
        Reservation.objects.filter(
            listing_id__in=listing_ids, status=ReservationStatus.RESERVED
        ).values_list("household_id", flat=True)
    )
    contacts = household_queries.email_contacts(household_ids)
    return sum(1 for email, _language in contacts.values() if email)


# One row of a household's history before the listing and store are added.
HISTORY_FIELDS = (
    "id",
    "listing_id",
    "quantity",
    "status",
    "pickup_code",
    "picked_up_at",
    "pickup_start",
    "pickup_end",
    "upcoming",
)


def _upcoming_at(moment: datetime) -> Case:
    """BR-RES-012: still ``reserved``, and the pickup window not ended at ``moment``.

    The end is included, as for confirming (BR-RES-002).
    """
    return Case(
        When(
            status=ReservationStatus.RESERVED,
            pickup_end__gte=moment,
            then=Value(True),
        ),
        default=Value(False),
        output_field=BooleanField(),
    )


def household_history(
    household_id: UUID | None,
    *,
    now: datetime,
    as_of: datetime | None = None,
    status: str | None = None,
) -> QuerySet[Reservation, dict[str, Any]]:
    """A household's reservations for its pickup history (US-48, BR-RES-012).

    Reservations upcoming at ``as_of`` come first, soonest pickup first; every
    other reservation follows, latest pickup window first. The order ends with
    the ID. Pass the time page 1 was read as ``as_of`` (default ``now``) for
    every page: a window that ends between two pages then cannot move a row
    across them. ``upcoming`` itself, which decides the pickup code, is at
    ``now``. ``status`` keeps one status only. No household (None) gives no rows.

    Rows only, so the caller can page them; ``history_entries`` then adds the
    listing and store of one page.
    """
    if household_id is None:
        rows = Reservation.objects.none()
    else:
        rows = Reservation.objects.filter(household_id=household_id)
    if status is not None:
        rows = rows.filter(status=status)
    # rule: BR-RES-012 upcoming: reserved, and the pickup window not ended.
    rows = rows.annotate(
        **listing_queries.pickup_window_of(OuterRef("listing_id"))
    ).annotate(
        upcoming=_upcoming_at(now),
        listed_upcoming=_upcoming_at(now if as_of is None else as_of),
    )
    soonest_upcoming = Case(
        When(listed_upcoming=True, then=F("pickup_start")),
        output_field=DateTimeField(),
    )
    return rows.order_by(
        F("listed_upcoming").desc(),
        soonest_upcoming.asc(nulls_last=True),
        F("pickup_start").desc(),
        "id",
    ).values(*HISTORY_FIELDS)


def history_entries(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each history row with its listing's title and unit and its store (US-48).

    The pickup code is sent only while the reservation is upcoming: a past code
    cannot be used any more (BR-RES-012).
    """
    rows = list(rows)
    listings = listing_queries.reserved_listing_details(
        {row["listing_id"] for row in rows}
    )
    return [
        {
            **listings[row["listing_id"]],
            **row,
            "pickup_code": row["pickup_code"] if row["upcoming"] else None,
        }
        for row in rows
    ]
