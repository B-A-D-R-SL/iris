# AI contribution: 50% or more AI-generated
"""Calendar-month expiry using the caller's file_validity rule value."""

import calendar
from datetime import datetime, timedelta

STATUS_APPROVED = "approved"
STATUS_RENEWAL_NEEDED = "renewal_needed"
STATUS_SUSPENDED = "suspended"


class InvalidApprovedMonths(ValueError):
    """``file_validity.approved_months`` is not a whole number of months above zero."""


def add_months(moment: datetime, months: int) -> datetime:
    """Use Montreal time before adding months: UTC can fall on a different day.

    Clamp month-end dates while keeping the local time and timezone.
    """
    if moment.tzinfo is None:
        raise ValueError("moment must be timezone-aware.")
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(moment.day, last_day)
    return moment.replace(year=year, month=month, day=day)


def approved_expiry(approved_at: datetime, approved_months: object) -> datetime:
    if type(approved_months) is not int or approved_months <= 0:
        raise InvalidApprovedMonths("approved_months must be a positive integer.")
    return add_months(approved_at, approved_months)


def expiry_for_status(
    status: str,
    moment: datetime,
    *,
    approved_until: datetime,
    renewal_overdue_by: timedelta,
    suspended_for: timedelta,
) -> datetime | None:
    if status == STATUS_RENEWAL_NEEDED:
        return moment - renewal_overdue_by
    if status == STATUS_SUSPENDED:
        return moment + suspended_for
    if status == STATUS_APPROVED:
        return approved_until
    return None
