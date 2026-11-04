# AI contribution: 50% or more AI-generated
"""US-34 safety rules, checked on every listing before it is published.

Pure Python: the posting service supplies the listing, a category snapshot and
the active ``listing_safety`` rule values. Every refusal is returned, not only
the first, so the form can show each problem next to its field.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from modules.listings.domain.posting import Refusal, SafetyRulesInvalid

__all__ = ["SafetyRulesInvalid", "SafetySettings", "check", "read_settings"]


@dataclass(frozen=True)
class SafetySettings:
    """The ``listing_safety`` rule values, checked."""

    prohibited_codes: frozenset[str]
    best_before_margin_days: int


def read_settings(rules: Any) -> SafetySettings:
    """Check every ``listing_safety`` value, or raise SafetyRulesInvalid.

    Posting and the posting form's category list both call this, so a broken
    rule blocks the form as soon as it opens instead of only at publish time.
    """
    # Stored values are a JSONField: a corrupted row could hold a list or scalar.
    if not isinstance(rules, Mapping):
        raise SafetyRulesInvalid("listing_safety values must be an object.")
    codes = rules.get("prohibited_category_codes")
    if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
        raise SafetyRulesInvalid("prohibited_category_codes must be a list of codes.")
    margin = rules.get("best_before_margin_days")
    # bool is an int subclass; True must not count as a one-day margin.
    if type(margin) is not int or margin < 0:
        raise SafetyRulesInvalid("best_before_margin_days must be a whole number >= 0.")
    return SafetySettings(frozenset(codes), margin)


def _calendar_date(value: Any, name: str) -> date:
    # datetime is a date subclass; a time of day here would be a caller bug.
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(f"{name} must be a calendar date.")
    return value


def check(
    listing_data: Mapping[str, Any],
    category: Mapping[str, Any],
    rules: Any,
) -> list[Refusal]:
    """Return every safety refusal for a listing; an empty list means safe.

    ``listing_data`` comes from ``posting.safety_payload``, ``category`` from
    ``categories.queries.for_listing_post`` and ``rules`` is the stored
    ``listing_safety`` values (checked by ``read_settings``).
    """
    settings = read_settings(rules)
    banned = settings.prohibited_codes
    margin_days = settings.best_before_margin_days
    refusals: list[Refusal] = []

    # rule: BR-LIST-001 safe-and-allowed confirmation on every post (also
    # checked by US-33's posting checks; kept here so edit and repost reuse
    # all rules).
    if listing_data.get("safe_and_allowed") is not True:
        refusals.append(Refusal("safe_and_allowed", "confirmation_required"))

    # rule: BR-LIST-002 categories on the prohibited list cannot be posted.
    if category["code"] in banned:
        refusals.append(Refusal("category", "category_prohibited"))

    # rule: BR-LIST-003 food needs a best-before date on or after the pickup
    # end date plus the configured margin. Non-food ignores any best-before date.
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
