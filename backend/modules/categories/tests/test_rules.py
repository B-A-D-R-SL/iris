# AI contribution: 50% or more AI-generated
"""Unit tests for pure category business rules."""

from datetime import date

import pytest

from modules.categories.domain.rules import (
    BestBeforeDateError,
    validate_best_before_date,
)


@pytest.mark.parametrize(
    "best_before",
    [None, date(2026, 11, 3)],
)
def test_non_food_does_not_require_best_before_date(
    best_before: date | None,
) -> None:
    """Non-food listings do not require a best-before date."""
    validate_best_before_date(
        is_food=False,
        best_before_date=best_before,
        pickup_end_date=date(2026, 11, 5),
        margin_days=0,
    )


def test_food_requires_best_before_date() -> None:
    """Food listings must have a best-before date."""
    with pytest.raises(BestBeforeDateError):
        validate_best_before_date(
            is_food=True,
            best_before_date=None,
            pickup_end_date=date(2026, 11, 5),
            margin_days=0,
        )


def test_food_rejects_expired_date() -> None:
    """Best-before date cannot precede pickup end date."""
    with pytest.raises(BestBeforeDateError):
        validate_best_before_date(
            is_food=True,
            best_before_date=date(2026, 11, 4),
            pickup_end_date=date(2026, 11, 5),
            margin_days=0,
        )


def test_food_accepts_same_day() -> None:
    """Same-day best-before date is valid when margin is zero."""
    validate_best_before_date(
        is_food=True,
        best_before_date=date(2026, 11, 5),
        pickup_end_date=date(2026, 11, 5),
        margin_days=0,
    )


def test_food_accepts_exact_margin() -> None:
    """A best-before date exactly at the configured margin is valid."""
    validate_best_before_date(
        is_food=True,
        best_before_date=date(2026, 11, 7),
        pickup_end_date=date(2026, 11, 5),
        margin_days=2,
    )


def test_food_rejects_insufficient_margin() -> None:
    """Food must satisfy the configured safety margin."""
    with pytest.raises(BestBeforeDateError):
        validate_best_before_date(
            is_food=True,
            best_before_date=date(2026, 11, 6),
            pickup_end_date=date(2026, 11, 5),
            margin_days=2,
        )


def test_negative_margin_is_rejected() -> None:
    """Negative safety margins are invalid configuration."""
    with pytest.raises(ValueError):
        validate_best_before_date(
            is_food=True,
            best_before_date=date(2026, 11, 7),
            pickup_end_date=date(2026, 11, 5),
            margin_days=-1,
        )
