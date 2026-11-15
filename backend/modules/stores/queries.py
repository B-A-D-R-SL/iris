# AI contribution: 50% or more AI-generated
"""Public read access; consumers never query Store's manager directly."""

from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import Count, Q, QuerySet, Value
from django.db.models.functions import Concat

from modules.listings import queries as listing_queries
from modules.reservations import queries as reservation_queries
from modules.stores.models import PartnerApplication, Store


def for_listing_post(store_id: UUID) -> Store | None:
    """Read and lock the store inside the caller's posting transaction."""
    return Store.objects.select_for_update().filter(pk=store_id).first()


def address(store_id: UUID) -> dict[str, Any] | None:
    """Listing locations always come from the offering store's address."""
    result = (
        Store.objects.filter(pk=store_id)
        .values("street_number", "street_name", "unit", "city", "postal_code")
        .first()
    )
    return dict(result) if result is not None else None


def partner_applications(status: str | None = None) -> QuerySet[PartnerApplication]:
    """Applications for the admin review list, oldest first (US-13)."""
    applications = PartnerApplication.objects.order_by("created_at", "id")
    if status:
        applications = applications.filter(status=status)
    return applications


def partner_application(application_id: UUID) -> PartnerApplication | None:
    """One application by ID, or None when it does not exist."""
    return PartnerApplication.objects.filter(pk=application_id).first()


# --- Store administration (US-14) -------------------------------------------

STATUS_FILTERS = {"active": True, "inactive": False}


def _search(q: str | None) -> QuerySet[Store]:
    """Stores whose name or address contains ``q`` (any case)."""
    stores = Store.objects.annotate(
        street=Concat("street_number", Value(" "), "street_name")
    )
    text = " ".join((q or "").split())
    if text:
        stores = stores.filter(
            Q(name__icontains=text)
            | Q(street__icontains=text)
            | Q(city__icontains=text)
            | Q(postal_code__icontains=text)
        )
    return stores


def staff_stores(q: str | None = None, status: str | None = None) -> QuerySet[Store]:
    """The admin store list: search, optional status, by name (W7.1)."""
    stores = _search(q)
    if status in STATUS_FILTERS:
        stores = stores.filter(is_active=STATUS_FILTERS[status])
    return stores.order_by("name", "id")


def status_counts(q: str | None = None) -> dict[str, int]:
    """Counts for the All / Active / Deactivated chips, for the same search."""
    counts = _search(q).aggregate(
        all=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        inactive=Count("id", filter=Q(is_active=False)),
    )
    return {key: counts[key] or 0 for key in ("all", "active", "inactive")}


def staff_store(store_id: UUID) -> Store | None:
    """One store for the admin edit screen, or None."""
    return Store.objects.filter(pk=store_id).first()


def open_listing_counts(store_ids: list[UUID], now: datetime) -> dict[UUID, int]:
    """Listings each store still offers for pickup (list column)."""
    return listing_queries.open_listing_counts(store_ids, now)


def deactivation_preview(store_id: UUID, now: datetime) -> dict[str, int]:
    """What deactivating now would cancel: listings and households to email."""
    listing_ids = listing_queries.open_listing_ids(store_id, now)
    return {
        "open_listings": len(listing_ids),
        "households_to_notify": reservation_queries.household_count_for_listings(
            listing_ids
        ),
    }
