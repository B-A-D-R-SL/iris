from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError

from modules.rules.domain.schemas import (
    DEFAULT_RULE_VALUES,
    RULE_SCHEMAS,
    RULE_TYPES,
    validate_rule_values,
)

VALID_LICO_VALUES = {
    "year": 2024,
    "source_url": "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110024101",
    "retrieved_on": "2026-10-16",
    "thresholds": {str(size): size * 1_000_000 for size in range(1, 8)},
}


@pytest.mark.parametrize("rule_type", RULE_TYPES)
def test_default_values_satisfy_each_rule_schema(rule_type: str) -> None:
    values = (
        VALID_LICO_VALUES
        if rule_type == "lico_thresholds"
        else DEFAULT_RULE_VALUES[rule_type]
    )

    validate_rule_values(rule_type, deepcopy(values))


@pytest.mark.parametrize(
    ("rule_type", "values", "message"),
    [
        (
            "lico_thresholds",
            {**VALID_LICO_VALUES, "thresholds": {"1": 1_000_000}},
            "required property",
        ),
        (
            "auto_approval",
            {**DEFAULT_RULE_VALUES["auto_approval"], "minimum_field_confidence": 1.1},
            "maximum of 1",
        ),
        (
            "priority",
            {**DEFAULT_RULE_VALUES["priority"], "child_points": -1},
            "minimum of 0",
        ),
        (
            "tiers",
            {**DEFAULT_RULE_VALUES["tiers"], "tier_3_pickup_window_ratio": 2},
            "maximum of 1",
        ),
        (
            "strikes",
            {**DEFAULT_RULE_VALUES["strikes"], "expires_after_days": 0},
            "minimum of 1",
        ),
        (
            "reservations",
            {**DEFAULT_RULE_VALUES["reservations"], "max_active_per_household": 0},
            "minimum of 1",
        ),
        (
            "listing_safety",
            {
                **DEFAULT_RULE_VALUES["listing_safety"],
                "prohibited_category_codes": ["Not a code"],
            },
            "does not match",
        ),
        (
            "file_validity",
            {**DEFAULT_RULE_VALUES["file_validity"], "reminder_days": [30, 30]},
            "non-unique elements",
        ),
        (
            "retention",
            {**DEFAULT_RULE_VALUES["retention"], "unexpected": 1},
            "Additional properties are not allowed",
        ),
    ],
)
def test_invalid_values_are_refused_with_a_clear_message(
    rule_type: str, values: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError) as caught:
        validate_rule_values(rule_type, values)

    assert message in caught.value.message_dict["values"][0]


def test_unknown_rule_type_is_refused() -> None:
    with pytest.raises(ValidationError, match="Unknown rule type 'unknown'"):
        validate_rule_values("unknown", {})


def test_every_supported_rule_type_has_exactly_one_schema() -> None:
    assert set(RULE_SCHEMAS) == set(RULE_TYPES)
    assert set(DEFAULT_RULE_VALUES) == set(RULE_TYPES) - {"lico_thresholds"}
