# AI contribution: 50% or more AI-generated
"""Household file expiry: month-end, leap years, and each status."""

from datetime import UTC, datetime, timedelta

import pytest

from modules.households.domain.expiry import (
    STATUS_APPROVED,
    STATUS_RENEWAL_NEEDED,
    STATUS_SUSPENDED,
    add_months,
    approved_expiry,
    expiry_for_status,
)

MORNING = datetime(2026, 1, 31, 15, 30, tzinfo=UTC)
SUSPENDED_FOR = timedelta(days=30)


def test_add_months_clamps_january_31_in_a_non_leap_year() -> None:
    """31 January 2026 plus one month is 28 February."""
    assert add_months(MORNING, 1) == datetime(2026, 2, 28, 15, 30, tzinfo=UTC)


def test_add_months_keeps_february_29_in_a_leap_year() -> None:
    """31 January 2024 plus one month is 29 February."""
    moment = MORNING.replace(year=2024)
    assert add_months(moment, 1) == datetime(2024, 2, 29, 15, 30, tzinfo=UTC)


def test_add_months_keeps_the_day_when_the_target_month_is_long_enough() -> None:
    """Twelve months from 31 January is 31 January the next year."""
    assert add_months(MORNING, 12) == datetime(2027, 1, 31, 15, 30, tzinfo=UTC)


def test_approved_expiry_uses_the_configured_month_count() -> None:
    assert approved_expiry(MORNING, 12) == add_months(MORNING, 12)


@pytest.mark.parametrize("months", [0, -1, True, 1.5, None, "12"])
def test_approved_expiry_rejects_a_month_count_that_is_not_a_positive_integer(
    months: object,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        approved_expiry(MORNING, months)


def test_approved_file_expires_at_the_configured_date() -> None:
    until = add_months(MORNING, 12)
    assert expiry_for_status(STATUS_APPROVED, MORNING, until, SUSPENDED_FOR) == until


def test_renewal_needed_file_is_already_one_day_past() -> None:
    until = add_months(MORNING, 12)
    assert expiry_for_status(
        STATUS_RENEWAL_NEEDED, MORNING, until, SUSPENDED_FOR
    ) == MORNING - timedelta(days=1)


def test_suspended_file_lasts_the_given_term() -> None:
    until = add_months(MORNING, 12)
    assert (
        expiry_for_status(STATUS_SUSPENDED, MORNING, until, SUSPENDED_FOR)
        == MORNING + SUSPENDED_FOR
    )


def test_other_statuses_have_no_expiry() -> None:
    until = add_months(MORNING, 12)
    assert expiry_for_status("draft", MORNING, until, SUSPENDED_FOR) is None
