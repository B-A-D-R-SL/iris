# AI contribution: 50% or more AI-generated
"""Public write interfaces for reservations."""

from collections import defaultdict
from uuid import UUID

from django.db import connection

from modules.listings import services as listing_services
from modules.reservations.models import Reservation, ReservationStatus


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
