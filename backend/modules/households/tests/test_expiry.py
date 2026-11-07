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
from modules.households.models import Household

JANUARY_31 = datetime(2026, 1, 31, 15, 30, tzinfo=UTC)
APPROVED_UNTIL = datetime(2027, 1, 31, 15, 30, tzinfo=UTC)
OVERDUE_BY = timedelta(days=1)
SUSPENDED_FOR = timedelta(days=30)


def expiry(status: str) -> datetime | None:
    return expiry_for_status(
        status,
        JANUARY_31,
        approved_until=APPROVED_UNTIL,
        renewal_overdue_by=OVERDUE_BY,
        suspended_for=SUSPENDED_FOR,
    )


def test_add_months_clamps_january_31_in_a_non_leap_year() -> None:
    """31 January 2026 plus one month is 28 February."""
    assert add_months(JANUARY_31, 1) == datetime(2026, 2, 28, 15, 30, tzinfo=UTC)


def test_add_months_keeps_february_29_in_a_leap_year() -> None:
    """31 January 2024 plus one month is 29 February."""
    moment = JANUARY_31.replace(year=2024)
    assert add_months(moment, 1) == datetime(2024, 2, 29, 15, 30, tzinfo=UTC)


def test_add_months_crosses_into_the_next_year() -> None:
    """15 November plus three months is 15 February of the next year."""
    moment = datetime(2026, 11, 15, 9, 0, tzinfo=UTC)
    assert add_months(moment, 3) == datetime(2027, 2, 15, 9, 0, tzinfo=UTC)


def test_add_months_refuses_a_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        add_months(JANUARY_31.replace(tzinfo=None), 1)


def test_approved_file_lasts_the_configured_number_of_months() -> None:
    """Twelve months from 31 January 2026 is 31 January 2027."""
    assert approved_expiry(JANUARY_31, 12) == APPROVED_UNTIL


@pytest.mark.parametrize("months", [0, -1, True, 1.5, None, "12"])
def test_approved_expiry_refuses_a_month_count_that_is_not_a_positive_integer(
    months: object,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        approved_expiry(JANUARY_31, months)


def test_approved_file_expires_on_its_approval_end_date() -> None:
    assert expiry(STATUS_APPROVED) == APPROVED_UNTIL


def test_renewal_needed_file_is_already_overdue() -> None:
    assert expiry(STATUS_RENEWAL_NEEDED) == datetime(2026, 1, 30, 15, 30, tzinfo=UTC)


def test_suspended_file_lasts_the_suspension_term() -> None:
    assert expiry(STATUS_SUSPENDED) == datetime(2026, 3, 2, 15, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    "status",
    [
        Household.Status.DRAFT,
        Household.Status.SUBMITTED,
        Household.Status.REVIEW_REQUIRED,
        Household.Status.AWAITING_VISIT,
        Household.Status.REJECTED,
    ],
)
def test_files_not_yet_approved_have_no_expiry(status: str) -> None:
    assert expiry(status) is None


def test_expiry_statuses_match_the_household_model() -> None:
    """The domain cannot import models, so its status names must stay in step."""
    assert STATUS_APPROVED == Household.Status.APPROVED
    assert STATUS_RENEWAL_NEEDED == Household.Status.RENEWAL_NEEDED
    assert STATUS_SUSPENDED == Household.Status.SUSPENDED
