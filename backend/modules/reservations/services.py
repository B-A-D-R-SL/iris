# AI contribution: 50% or more AI-generated
"""Public write interfaces for reservations.

Reserving a unit (US-41), pickup confirmation (US-44) and cancellation when a
household is suspended (US-32).
"""

import logging
import secrets
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from modules.households import services as household_services
from modules.listings import queries as listing_queries
from modules.listings import services as listing_services
from modules.reservations.domain import limits, pickup
from modules.reservations.domain.codes import Chooser, new_pickup_code
from modules.reservations.domain.pickup import PickupRefused
from modules.reservations.models import MadeByType, Reservation, ReservationStatus
from modules.reservations.permissions import pickup_store_id
from modules.reservations.queries import Pickup, confirmable_pickup
from modules.rules import queries as rule_queries

logger = logging.getLogger(__name__)


@transaction.atomic
def confirm_pickup(
    reservation_id: UUID, staff: Any, *, now: datetime | None = None
) -> Pickup:
    """Mark a reservation picked up, with who and when, exactly once.

    The row is locked, then the store, status and pickup window are checked
    again (BR-RES-001, BR-RES-002), so a double tap or two counters confirming
    at once give one pickup and one ``already_picked_up``. Listing stock is not
    changed: the units stay taken (BR-RES-005).
    """
    listings = listing_queries.pickup_listings(pickup_store_id(staff))
    reservation = (
        Reservation.objects.select_for_update()
        .filter(pk=reservation_id, listing_id__in=listings.values("id"))
        .first()
    )
    if reservation is None:
        raise PickupRefused(pickup.UNKNOWN_RESERVATION)
    # Waiting for the row lock can cross the pickup deadline.
    moment = timezone.now() if now is None else now
    shown = confirmable_pickup(
        reservation, listings.get(id=reservation.listing_id), now=moment
    )

    reservation.status = ReservationStatus.PICKED_UP
    reservation.picked_up_at = moment
    reservation.confirmed_by = staff
    reservation.save(update_fields=["status", "picked_up_at", "confirmed_by"])
    transaction.on_commit(
        lambda: logger.info("pickup_confirmed", extra={"event": "pickup_confirmed"})
    )
    return replace(shown, status=reservation.status, picked_up_at=moment)


def cancel_open_for_household(household_id: UUID) -> int:
    """Cancel every reserved claim without a late-cancellation strike."""
    if not connection.in_atomic_block:
        raise RuntimeError("Reservation cancellation must run inside a transaction.")
    reservations = list(
        Reservation.objects.select_for_update()
        .filter(household_id=household_id, status=ReservationStatus.RESERVED)
        .order_by("pk")
    )
    released: dict[UUID, int] = defaultdict(int)
    for reservation in reservations:
        released[reservation.listing_id] += reservation.quantity
    for listing_id, quantity in sorted(released.items()):
        listing_services.release_units(listing_id, quantity)
    if reservations:
        Reservation.objects.filter(pk__in=[item.pk for item in reservations]).update(
            status=ReservationStatus.CANCELLED, late_cancel=False
        )
    return len(reservations)


# Refusal codes the API turns into a status and a translated message.
HOUSEHOLD_NOT_APPROVED = "household_not_approved"
RESERVATIONS_UNAVAILABLE = "reservations_unavailable"
LISTING_NOT_AVAILABLE = "listing_not_available"
SOLD_OUT = "sold_out"
NOT_ENOUGH_UNITS = "not_enough_units"
QUANTITY_OVER_LISTING_LIMIT = limits.QUANTITY_OVER_LISTING_LIMIT
TOO_MANY_ACTIVE_RESERVATIONS = limits.TOO_MANY_ACTIVE_RESERVATIONS
PICKUP_CODE_UNAVAILABLE = "pickup_code_unavailable"

# A clash is about 1 in 887 million per reservation on a listing, so five
# tries in a row failing means something else is wrong.
CODE_ATTEMPTS = 5
CODE_CONSTRAINT = "reservations_listing_pickup_code_uniq"


class ReservationRefused(Exception):
    """The reservation was not made; ``code`` says why. Nothing was changed."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _max_active(now: datetime) -> int:
    """The ``reservations`` rule in effect; refuse when there is none."""
    rules = rule_queries.active("reservations", at=now)
    if rules is None:
        raise ReservationRefused(RESERVATIONS_UNAVAILABLE)
    try:
        return limits.read_max_active(rules.values)
    except limits.ReservationRulesInvalid as exc:
        raise ReservationRefused(RESERVATIONS_UNAVAILABLE) from exc


def _holding(household_id: UUID, listing_id: UUID) -> limits.Holding:
    """What the household holds now; only ``reserved`` counts as active."""
    totals = Reservation.objects.filter(
        household_id=household_id, status=ReservationStatus.RESERVED
    ).aggregate(
        active=Count("id"),
        on_listing=Sum("quantity", filter=Q(listing_id=listing_id), default=0),
    )
    return limits.Holding(
        active_reservations=totals["active"],
        quantity_on_listing=totals["on_listing"],
    )


def _is_code_clash(exc: IntegrityError) -> bool:
    """True when the insert failed only because the pickup code was taken."""
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) == CODE_CONSTRAINT


def _insert(
    user: Any, household_id: UUID, listing_id: UUID, quantity: int, choose: Chooser
) -> Reservation:
    """Save the reservation, drawing a new code if one is already used."""
    for _attempt in range(CODE_ATTEMPTS):
        try:
            # A savepoint: a code clash undoes only this insert, not the units.
            with transaction.atomic():
                return Reservation.objects.create(
                    listing_id=listing_id,
                    household_id=household_id,
                    quantity=quantity,
                    pickup_code=new_pickup_code(choose),
                    status=ReservationStatus.RESERVED,
                    made_by_type=MadeByType.HOUSEHOLD,
                    made_by=user,
                )
        except IntegrityError as exc:
            if not _is_code_clash(exc):
                raise
    raise ReservationRefused(PICKUP_CODE_UNAVAILABLE)


def _check_request(
    household_id: UUID, listing_id: UUID, quantity: int, moment: datetime
) -> None:
    """Every refusal that needs no change: rules, listing, limits and stock.

    Runs after the household lock and before any write, so a refusal leaves
    nothing to undo. The order sets which reason the household hears first.
    """
    max_active = _max_active(moment)
    listing = listing_queries.reservable_listing(household_id, listing_id, moment)
    if listing is None:
        raise ReservationRefused(LISTING_NOT_AVAILABLE)
    if listing["units_left"] == 0:
        raise ReservationRefused(SOLD_OUT)
    reasons = limits.refusals(
        quantity,
        _holding(household_id, listing_id),
        max_per_household=listing["max_per_household"],
        max_active=max_active,
    )
    if reasons:
        raise ReservationRefused(reasons[0])
    if quantity > listing["units_left"]:
        raise ReservationRefused(NOT_ENOUGH_UNITS)


@transaction.atomic
def reserve(
    user: Any,
    household_id: UUID,
    listing_id: UUID,
    quantity: int,
    *,
    now: datetime | None = None,
    choose: Chooser = secrets.choice,
) -> Reservation:
    """Reserve ``quantity`` units of a listing for a household, all or nothing.

    ``user`` is the signed-in account holder making the reservation. Raises
    ReservationRefused, with nothing changed, when the household is not
    approved (BR-RES-006), the listing cannot be reserved, a limit is reached
    (BR-RES-007, BR-RES-008) or the units are gone (BR-RES-009). Otherwise the
    units are taken and the reservation saved with a new pickup code
    (BR-RES-010) in one transaction.
    """
    if quantity < 1:
        raise ValueError("quantity must be 1 or more.")
    moment = timezone.now() if now is None else now

    # 1. Lock the household first, so its reservations run one at a time.
    # rule: BR-RES-006 only an approved household that has not expired.
    if not household_services.lock_approved_household(household_id, at=moment):
        raise ReservationRefused(HOUSEHOLD_NOT_APPROVED)
    # TODO(strikes story): refuse a household blocked by strikes here.

    # 2. Every check that needs no change. Nothing has been changed yet.
    _check_request(household_id, listing_id, quantity, moment)

    # 3. Take the units and save the reservation together.
    if not listing_services.take_units(listing_id, quantity, now=moment):
        # Someone else took them between the read above and this update.
        raise ReservationRefused(SOLD_OUT)
    reservation = _insert(user, household_id, listing_id, quantity, choose)
    # No names, codes or IDs in the log line.
    transaction.on_commit(
        lambda: logger.info("reservation_created", extra={"event": "created"})
    )
    return reservation
