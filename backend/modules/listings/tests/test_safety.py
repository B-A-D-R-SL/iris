# AI contribution: 50% or more AI-generated
"""US-34 safety rule: one test (or more) per refusal reason, no database."""

from datetime import UTC, date, datetime
from typing import Any

import pytest

from modules.listings.domain.posting import Refusal, SafetyRulesInvalid
from modules.listings.domain.safety import SafetySettings, check, read_settings

PICKUP_END = date(2026, 11, 13)
FOOD = {"code": "bakery", "is_food": True}
NON_FOOD = {"code": "clothing", "is_food": False}
DEFAULT_RULES = {"best_before_margin_days": 0, "prohibited_category_codes": []}


def listing(**changes: Any) -> dict[str, Any]:
    return {
        "pickup_end_date": PICKUP_END,
        "best_before": PICKUP_END,
        "safe_and_allowed": True,
        **changes,
    }


def rules(**changes: Any) -> dict[str, Any]:
    return {**DEFAULT_RULES, **changes}


def test_us34_safe_listing_has_no_refusals() -> None:
    assert check(listing(), FOOD, rules()) == []


# rule: BR-LIST-001 safe-and-allowed confirmation on every post
@pytest.mark.parametrize("ticked", [False, None, 1, "true"])
def test_us34_refuses_listing_without_safe_and_allowed_tick(ticked: Any) -> None:
    assert check(listing(safe_and_allowed=ticked), FOOD, rules()) == [
        Refusal("safe_and_allowed", "confirmation_required")
    ]


# rule: BR-LIST-002 categories on the prohibited list cannot be posted
def test_us34_refuses_category_on_prohibited_list() -> None:
    banned = rules(prohibited_category_codes=["bakery", "beverages"])
    assert check(listing(), FOOD, banned) == [
        Refusal("category", "category_prohibited")
    ]


@pytest.mark.parametrize("codes", [[], ["beverages"]])
def test_us34_accepts_category_not_on_prohibited_list(codes: list[str]) -> None:
    assert check(listing(), FOOD, rules(prohibited_category_codes=codes)) == []


# rule: BR-LIST-003 food needs a best-before date
def test_us34_refuses_food_without_best_before() -> None:
    assert check(listing(best_before=None), FOOD, rules()) == [
        Refusal("best_before", "best_before_required")
    ]


# rule: BR-LIST-003 food best-before on or after the pickup end date plus the margin
@pytest.mark.parametrize(
    ("margin", "best_before", "earliest"),
    [
        (0, date(2026, 11, 12), date(2026, 11, 13)),
        (1, date(2026, 11, 13), date(2026, 11, 14)),
        (2, date(2026, 11, 14), date(2026, 11, 15)),
    ],
)
def test_us34_refuses_best_before_earlier_than_pickup_end_plus_margin(
    margin: int, best_before: date, earliest: date
) -> None:
    refusals = check(
        listing(best_before=best_before), FOOD, rules(best_before_margin_days=margin)
    )
    assert refusals == [
        Refusal("best_before", "best_before_too_early", {"date": earliest})
    ]


@pytest.mark.parametrize(
    ("margin", "best_before"),
    [
        (0, date(2026, 11, 13)),  # on the pickup end date: accepted
        (0, date(2026, 11, 20)),
        (1, date(2026, 11, 14)),
        (2, date(2026, 11, 15)),
    ],
)
def test_us34_accepts_best_before_on_or_after_pickup_end_plus_margin(
    margin: int, best_before: date
) -> None:
    assert (
        check(
            listing(best_before=best_before),
            FOOD,
            rules(best_before_margin_days=margin),
        )
        == []
    )


# rule: BR-LIST-003 non-food ignores the best-before date
@pytest.mark.parametrize("best_before", [None, date(2026, 1, 1)])
def test_us34_non_food_ignores_best_before(best_before: date | None) -> None:
    assert check(listing(best_before=best_before), NON_FOOD, rules()) == []


def test_us34_returns_every_refusal_at_once() -> None:
    refusals = check(
        listing(best_before=date(2026, 11, 1), safe_and_allowed=False),
        FOOD,
        rules(prohibited_category_codes=["bakery"]),
    )
    assert [(r.field, r.code) for r in refusals] == [
        ("safe_and_allowed", "confirmation_required"),
        ("category", "category_prohibited"),
        ("best_before", "best_before_too_early"),
    ]


def test_us34_read_settings_returns_both_values() -> None:
    assert read_settings(
        rules(prohibited_category_codes=["a", "b"], best_before_margin_days=2)
    ) == SafetySettings(frozenset({"a", "b"}), 2)
    assert read_settings(rules()) == SafetySettings(frozenset(), 0)


MALFORMED_RULES: list[Any] = [
    # Not an object at all (a corrupted JSONField row).
    [],
    None,
    "listing_safety",
    # Bad or missing margin.
    {"best_before_margin_days": -1, "prohibited_category_codes": []},
    {"best_before_margin_days": True, "prohibited_category_codes": []},
    {"best_before_margin_days": 1.5, "prohibited_category_codes": []},
    {"prohibited_category_codes": []},
    # Bad or missing prohibited list.
    {"best_before_margin_days": 0, "prohibited_category_codes": "bakery"},
    {"best_before_margin_days": 0, "prohibited_category_codes": [1]},
    {"best_before_margin_days": 0},
]


@pytest.mark.parametrize("bad_rules", MALFORMED_RULES)
def test_us34_read_settings_rejects_malformed_rules(bad_rules: Any) -> None:
    with pytest.raises(SafetyRulesInvalid):
        read_settings(bad_rules)


@pytest.mark.parametrize(
    "bad_rules",
    [
        {"best_before_margin_days": -1, "prohibited_category_codes": []},
        {"best_before_margin_days": True, "prohibited_category_codes": []},
        {"best_before_margin_days": 1.5, "prohibited_category_codes": []},
        {"prohibited_category_codes": []},
        {"best_before_margin_days": 0, "prohibited_category_codes": "bakery"},
        {"best_before_margin_days": 0, "prohibited_category_codes": [1]},
        {"best_before_margin_days": 0},
        [],
    ],
)
def test_us34_malformed_safety_rules_raise(bad_rules: Any) -> None:
    with pytest.raises(SafetyRulesInvalid):
        check(listing(), FOOD, bad_rules)


def test_us34_non_food_still_refused_when_margin_is_malformed() -> None:
    # The margin only matters for food, but a broken rule blocks every post.
    with pytest.raises(SafetyRulesInvalid):
        check(listing(), NON_FOOD, rules(best_before_margin_days=-1))


def test_us34_margin_past_the_last_calendar_date_raises() -> None:
    with pytest.raises(SafetyRulesInvalid, match="too large"):
        check(listing(), FOOD, rules(best_before_margin_days=10**7))


@pytest.mark.parametrize(
    "changes",
    [
        {"best_before": datetime(2026, 11, 13, 12, tzinfo=UTC)},
        {"best_before": "2026-11-13"},
        {"pickup_end_date": datetime(2026, 11, 13, 12, tzinfo=UTC)},
        {"pickup_end_date": None},
    ],
)
def test_us34_rejects_non_calendar_dates_from_the_caller(
    changes: dict[str, Any],
) -> None:
    with pytest.raises(TypeError):
        check(listing(**changes), FOOD, rules())
