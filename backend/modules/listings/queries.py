# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for listings."""

from datetime import datetime
from typing import Any
from uuid import UUID

from django.db.models import F, QuerySet
from django.utils import timezone

from modules.categories import queries as category_queries
from modules.listings.domain.browsing import end_of_local_day
from modules.listings.domain.safety import read_settings
from modules.listings.models import Listing, ListingStatus
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
