# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for listings."""

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import Count, F, QuerySet, Subquery, Value
from django.utils import timezone

from modules.categories import queries as category_queries
from modules.listings.domain.browsing import end_of_local_day
from modules.listings.domain.safety import read_settings
from modules.listings.models import Listing, ListingStatus
from modules.listings.photo_storage import read_urls
from modules.rules import queries as rule_queries

POSTING_CATEGORY_FIELDS = (
    "code",
    "name_fr",
    "name_en",
    "is_food",
    "default_value_cents",
)

# One card in the browse list (US-36). The store's name and address come in the
# same query, so a page of cards never needs one query per listing.
LISTING_CARD_FIELDS = (
    "id",
    "title",
    "unit",
    "pickup_start",
    "pickup_end",
    "best_before",
    "store_id",
    "photo_ref",
    "max_per_household",  # US-41: the Reserve button's quantity limit
)
LISTING_CARD_EXPRESSIONS = {
    "units_left": F("quantity_total") - F("quantity_reserved"),
    "category_code": F("category__code"),
    "store_name": F("store__name"),
    "store_street_number": F("store__street_number"),
    "store_street_name": F("store__street_name"),
    "store_unit": F("store__unit"),
    "store_city": F("store__city"),
    "store_postal_code": F("store__postal_code"),
}
# The offering store under the same names as on a card, for the pickup history
# (US-48), so both screens read the store the same way.
STORE_EXPRESSIONS = {
    name: expression
    for name, expression in LISTING_CARD_EXPRESSIONS.items()
    if name.startswith("store_")
}


def photo_read_urls(references: list[str]) -> dict[str, str]:
    """For server-filtered cards only; never accepts a client-submitted reference."""
    return read_urls(references)


def categories_for_posting(*, at: datetime) -> list[dict[str, Any]] | None:
    """Active categories a store may post in at ``at``: banned codes left out.

    Returns None when no ``listing_safety`` rule version is in effect. Raises
    SafetyRulesInvalid when any of that version's values is malformed (the
    same check as posting), so the form does not open only to fail at publish.
    """
    rules = rule_queries.active("listing_safety", at=at)
    if rules is None:
        return None
    banned = read_settings(rules.values).prohibited_codes
    return [
        category
        for category in category_queries.list_active_categories().values(
            *POSTING_CATEGORY_FIELDS
        )
        if category["code"] not in banned
    ]


def pickup_listings(store_id: UUID) -> QuerySet[Listing, Any]:
    """The store's listings as plain values, for pickup lookup and confirmation (US-44).

    Reservations filters its own rows with ``.values("id")`` of this result as a
    subquery, so a pickup never reads another store's listings.
    """
    return Listing.objects.filter(store_id=store_id).values(
        "id", "title", "unit", "pickup_start", "pickup_end"
    )


def visible_listings(household_id: UUID | None, now: datetime) -> QuerySet[Listing]:
    """The listings a household can see at ``now``; the only place this is decided.

    A household sees a listing when it is published, has units left and its
    pickup has not ended (BR-LIST-004). Until tiers exist (US-51) every
    approved household sees every such listing; the tier delay belongs here.
    Without an approved household (None) nothing is visible. Callers check
    approval first and refuse the request.
    """
    if now.utcoffset() is None:
        raise ValueError("The supplied clock must be timezone-aware.")
    if household_id is None:
        return Listing.objects.none()
    # rule: BR-LIST-004 published, with units left, and the pickup not ended.
    return Listing.objects.filter(
        status=ListingStatus.PUBLISHED,
        quantity_reserved__lt=F("quantity_total"),
        pickup_end__gt=now,
    )


def reservable_listing(
    household_id: UUID | None, listing_id: UUID, now: datetime
) -> dict[str, Any] | None:
    """The limits a household needs to reserve a listing it can see (US-41).

    Uses ``visible_listings``, so a listing the household cannot see (closed,
    cancelled, ended, or later its tier delay) cannot be reserved either.
    Returns ``{"id", "max_per_household", "units_left"}``, or None.

    A listing that is open but has no units left is not visible, yet the
    household should hear "sold out", not "not available": it is returned
    with ``units_left`` 0. Stock is only ever taken by ``services.take_units``.
    """
    fields = ("id", "max_per_household")
    found = (
        visible_listings(household_id, now)
        .filter(pk=listing_id)
        .values(*fields, units_left=F("quantity_total") - F("quantity_reserved"))
        .first()
    )
    if found is not None or household_id is None:
        return found
    return (
        Listing.objects.filter(
            pk=listing_id,
            status=ListingStatus.PUBLISHED,
            pickup_end__gt=now,
            quantity_reserved__gte=F("quantity_total"),
        )
        .values(*fields, units_left=Value(0))
        .first()
    )


def browse_listings(
    household_id: UUID | None,
    now: datetime,
    *,
    category: str | None = None,
    store: UUID | None = None,
    pickup_today: bool = False,
) -> QuerySet[Listing, dict[str, Any]]:
    """Visible listings as cards, filtered and sorted by pickup start (US-36).

    ``category`` is a category code and ``store`` a store ID; one that does
    not exist matches nothing. ``pickup_today`` keeps listings that can still
    be picked up today, Montreal time (BR-LIST-005). Listings with the same
    pickup start are ordered by ID, so pages never repeat or skip one.
    """
    listings = visible_listings(household_id, now)
    if category is not None:
        listings = listings.filter(category__code=category)
    if store is not None:
        listings = listings.filter(store_id=store)
    if pickup_today:
        listings = listings.filter(
            pickup_start__lt=end_of_local_day(now, timezone.get_default_timezone())
        )
    return listings.order_by("pickup_start", "id").values(
        *LISTING_CARD_FIELDS, **LISTING_CARD_EXPRESSIONS
    )


def _open_for_pickup(now: datetime) -> QuerySet[Listing]:
    """Published listings whose pickup has not ended: what deactivation cancels."""
    return Listing.objects.filter(status=ListingStatus.PUBLISHED, pickup_end__gt=now)


def open_listing_counts(store_ids: list[UUID], now: datetime) -> dict[UUID, int]:
    """Open listings per store, for the admin store list (US-14)."""
    rows = (
        _open_for_pickup(now)
        .filter(store_id__in=store_ids)
        .values("store_id")
        .annotate(total=Count("id"))
    )
    return {row["store_id"]: row["total"] for row in rows}


def open_listing_ids(store_id: UUID, now: datetime) -> list[UUID]:
    """The listings a deactivation would cancel now, for its confirmation (US-14)."""
    return list(
        _open_for_pickup(now).filter(store_id=store_id).values_list("pk", flat=True)
    )


def cancellation_details(listing_ids: list[UUID]) -> dict[UUID, str]:
    """Listing titles for the store cancellation emails (US-14)."""
    rows = Listing.objects.filter(pk__in=listing_ids).values_list("pk", "title")
    return dict(rows)


def pickup_window_of(listing_ref: Any) -> dict[str, Subquery]:
    """The pickup start and end of the listing ``listing_ref`` names, as subqueries.

    ``listing_ref`` is usually ``OuterRef("listing_id")``. Reservations annotates
    its own rows with them to sort a household's history by pickup window
    (US-48) without reading the listings table itself.
    """
    listing = Listing.objects.filter(pk=listing_ref)
    return {
        "pickup_start": Subquery(listing.values("pickup_start")[:1]),
        "pickup_end": Subquery(listing.values("pickup_end")[:1]),
    }


def reserved_listing_details(
    listing_ids: Iterable[UUID],
) -> dict[UUID, dict[str, Any]]:
    """Title, unit and store of each listing, by listing ID (US-48).

    Every status counts: a reservation keeps showing its listing after the
    listing closes or is cancelled. One query covers a whole page of history.
    """
    rows: QuerySet[Listing, Any] = Listing.objects.filter(
        pk__in=list(listing_ids)
    ).values("id", "title", "unit", "store_id", **STORE_EXPRESSIONS)
    return {
        row["id"]: {name: value for name, value in row.items() if name != "id"}
        for row in rows
    }
