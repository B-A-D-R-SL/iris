# AI contribution: 50% or more AI-generated
"""Versioned US-33 limits stay within the existing model's physical bounds."""

from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError

from modules.rules.domain.schemas import DEFAULT_RULE_VALUES, validate_rule_values


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("title_max_length", 81),
        ("description_max_length", 501),
        ("quantity_max", 1000),
        ("max_per_household", 11),
        ("estimated_value_max_cents", 100_001),
        ("pickup_start_max_days", 0),
        ("pickup_min_minutes", 0),
        ("photo_max_bytes", 0),
        ("photo_max_dimension", 0),
    ],
)
def test_us33_posting_configuration_rejects_invalid_limits(
    field: str, invalid: int
) -> None:
    values = {**deepcopy(DEFAULT_RULE_VALUES["listing_posting"]), field: invalid}
    with pytest.raises(ValidationError):
        validate_rule_values("listing_posting", values)


@pytest.mark.parametrize(
    "changes",
    [
        {"title_min_length": 10, "title_max_length": 5},
        {"pickup_min_minutes": 100, "pickup_max_minutes": 60},
    ],
)
def test_us33_posting_minimums_cannot_exceed_maximums(changes: dict[str, int]) -> None:
    with pytest.raises(ValidationError, match="minimums"):
        validate_rule_values(
            "listing_posting", {**DEFAULT_RULE_VALUES["listing_posting"], **changes}
        )
