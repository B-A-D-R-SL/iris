# AI contribution: 50% or more AI-generated
"""Public write interfaces for reservations: pickup confirmation and cancellation."""

import logging
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import connection, transaction
from django.utils import timezone

from modules.listings import queries as listing_queries
from modules.listings import services as listing_services
from modules.reservations.domain import pickup
from modules.reservations.domain.pickup import PickupRefused
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.permissions import pickup_store_id
from modules.reservations.queries import Pickup, confirmable_pickup

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
