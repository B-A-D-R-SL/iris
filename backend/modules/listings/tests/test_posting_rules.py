# AI contribution: 50% or more AI-generated
"""US-33 boundaries using plain Python inputs; no Django/database fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from modules.listings.domain.posting import ListingInput, PostingLimits, check_posting

NOW = datetime(2026, 10, 27, 18, tzinfo=UTC)
LIMITS = PostingLimits(
    title_min_length=2,
    title_max_length=80,
    description_max_length=500,
    quantity_max=999,
    max_per_household=10,
    estimated_value_max_cents=100_000,
    pickup_start_max_days=7,
    pickup_min_minutes=30,
    pickup_max_minutes=720,
    photo_max_bytes=5 * 1024 * 1024,
    photo_max_dimension=1280,
)
DATA = ListingInput(
    category="bakery",
    title="Bread",
    quantity=1,
    pickup_start=NOW + timedelta(hours=1),
    pickup_end=NOW + timedelta(hours=2),
    safe_and_allowed=True,
)


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "AB"},
        {"title": "A" * 80},
        {"description": "D" * 500},
        {"quantity": 999},
        {"max_per_household": 10},
        {"unit": "bundle"},
        {"estimated_value_cents": 0},
        {"estimated_value_cents": 100_000},
        {"pickup_start": NOW, "pickup_end": NOW + timedelta(minutes=30)},
        {
            "pickup_start": NOW + timedelta(days=7),
            "pickup_end": NOW + timedelta(days=7, hours=12),
        },
    ],
)
def test_us33_accepts_inclusive_boundaries(changes: dict[str, Any]) -> None:
    assert check_posting(replace(DATA, **changes), LIMITS, now=NOW) == []


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"title": "A"}, "title"),
        ({"title": " " * 5}, "title"),
        ({"title": "A" * 81}, "title"),
        ({"description": "D" * 501}, "description"),
        ({"quantity": 0}, "quantity"),
        ({"quantity": 1000}, "quantity"),
        ({"quantity": True}, "quantity"),
        ({"quantity": 1.5}, "quantity"),
        ({"max_per_household": 0}, "max_per_household"),
        ({"max_per_household": 11}, "max_per_household"),
        ({"max_per_household": True}, "max_per_household"),
        ({"unit": "box"}, "unit"),
        ({"estimated_value_cents": -1}, "estimated_value_cents"),
        ({"estimated_value_cents": 100_001}, "estimated_value_cents"),
        ({"estimated_value_cents": 0.5}, "estimated_value_cents"),
        ({"estimated_value_cents": False}, "estimated_value_cents"),
        ({"safe_and_allowed": False}, "safe_and_allowed"),
        ({"safe_and_allowed": 1}, "safe_and_allowed"),
        ({"pickup_start": NOW - timedelta(microseconds=1)}, "pickup_start"),
        ({"pickup_start": NOW + timedelta(days=7, microseconds=1)}, "pickup_start"),
        (
            {"pickup_end": DATA.pickup_start + timedelta(minutes=30, microseconds=-1)},
            "pickup_end",
        ),
        (
            {"pickup_end": DATA.pickup_start + timedelta(hours=12, microseconds=1)},
            "pickup_end",
        ),
        ({"pickup_end": DATA.pickup_start}, "pickup_end"),
        ({"pickup_start": DATA.pickup_start.replace(tzinfo=None)}, "pickup_start"),
        ({"pickup_end": DATA.pickup_end.replace(tzinfo=None)}, "pickup_end"),
    ],
)
def test_us33_rejects_invalid_fields(changes: dict[str, Any], field: str) -> None:
    assert field in {
        reason.field
        for reason in check_posting(replace(DATA, **changes), LIMITS, now=NOW)
    }


def test_us33_uses_supplied_limits_instead_of_fixed_defaults() -> None:
    limits = replace(LIMITS, quantity_max=3, pickup_min_minutes=180)
    reasons = check_posting(replace(DATA, quantity=4), limits, now=NOW)
    assert {reason.field for reason in reasons} == {"quantity", "pickup_end"}


def test_us33_uses_elapsed_time_across_montreal_dst_change() -> None:
    montreal = ZoneInfo("America/Montreal")
    start = datetime(2026, 11, 1, 1, 45, tzinfo=montreal, fold=0)
    end = datetime(2026, 11, 1, 1, 15, tzinfo=montreal, fold=1)
    data = replace(DATA, pickup_start=start, pickup_end=end)
    assert check_posting(data, LIMITS, now=start.astimezone(UTC)) == []


def test_us33_requires_an_aware_clock() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        check_posting(DATA, LIMITS, now=NOW.replace(tzinfo=None))
