# AI contribution: 50% or more AI-generated
"""US-34 safety rules, checked on every listing before it is published.

Pure Python: the posting service supplies the listing, a category snapshot and
the active ``listing_safety`` rule values. Every refusal is returned, not only
the first, so the form can show each problem next to its field.
"""

from collections.abc import Mapping
from datetime import date, datetime, timedelta
from typing import Any

from modules.listings.domain.posting import Refusal, SafetyRulesInvalid

__all__ = ["SafetyRulesInvalid", "check", "prohibited_codes"]


def prohibited_codes(rules: Mapping[str, Any]) -> frozenset[str]:
    """Return the banned category codes, or raise if the setting is malformed."""
    codes = rules.get("prohibited_category_codes")
    if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
        raise SafetyRulesInvalid("prohibited_category_codes must be a list of codes.")
    return frozenset(codes)


def _margin_days(rules: Mapping[str, Any]) -> int:
    margin = rules.get("best_before_margin_days")
    # bool is an int subclass; True must not count as a one-day margin.
    if type(margin) is not int or margin < 0:
        raise SafetyRulesInvalid("best_before_margin_days must be a whole number >= 0.")
    return margin


def _calendar_date(value: Any, name: str) -> date:
    # datetime is a date subclass; a time of day here would be a caller bug.
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{name} must be a calendar date.")
    return value


def check(
    listing_data: Mapping[str, Any],
    category: Mapping[str, Any],
    rules: Mapping[str, Any],
) -> list[Refusal]:
    """Return every safety refusal for a listing; an empty list means safe.

    ``listing_data`` comes from ``posting.safety_payload`` and ``category`` from
    ``categories.queries.for_listing_post``.
    """
    banned = prohibited_codes(rules)
    margin_days = _margin_days(rules)
    refusals: list[Refusal] = []

    # rule: safe-and-allowed confirmation on every post (also checked by
    # US-33's posting checks; kept here so edit and repost reuse all rules).
    if listing_data.get("safe_and_allowed") is not True:
        refusals.append(Refusal("safe_and_allowed", "confirmation_required"))

    # rule: categories on the prohibited list cannot be posted.
    if category["code"] in banned:
        refusals.append(Refusal("category", "category_prohibited"))

    # rule: food needs a best-before date on or after the pickup end date
    # plus the configured margin. Non-food ignores any best-before date.
    if category["is_food"] is True:
        best_before = listing_data.get("best_before")
        if best_before is None:
            refusals.append(Refusal("best_before", "best_before_required"))
        else:
            pickup_end_date = _calendar_date(
                listing_data.get("pickup_end_date"), "pickup_end_date"
            )
            try:
                earliest = pickup_end_date + timedelta(days=margin_days)
            except OverflowError as exc:
                raise SafetyRulesInvalid(
                    "best_before_margin_days is too large."
                ) from exc
            if _calendar_date(best_before, "best_before") < earliest:
                refusals.append(
                    Refusal("best_before", "best_before_too_early", {"date": earliest})
                )
    return refusals
