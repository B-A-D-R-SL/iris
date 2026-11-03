# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for listings."""

from datetime import datetime
from typing import Any

from modules.categories import queries as category_queries
from modules.listings.domain.safety import prohibited_codes
from modules.rules import queries as rule_queries

POSTING_CATEGORY_FIELDS = (
    "code",
    "name_fr",
    "name_en",
    "is_food",
    "default_value_cents",
)


def categories_for_posting(*, at: datetime) -> list[dict[str, Any]] | None:
    """Active categories a store may post in at ``at``: banned codes left out.

    Returns None when no ``listing_safety`` rule version is in effect. Raises
    SafetyRulesInvalid when that version's values are malformed.
    """
    rules = rule_queries.active("listing_safety", at=at)
    if rules is None:
        return None
    banned = prohibited_codes(rules.values)
    return [
        category
        for category in category_queries.list_active_categories().values(
            *POSTING_CATEGORY_FIELDS
        )
        if category["code"] not in banned
    ]
