# AI contribution: 50% or more AI-generated
"""When a household file expires. Plain dates, no database and no Django.

US-18's approval service and the seed command both call these functions, so
the length of an approved file lives in one place. The month count comes from
the ``file_validity.approved_months`` rule; callers pass it in.
"""

import calendar
from datetime import datetime, timedelta

# Household.Status in models.py builds its choices from these.
STATUS_APPROVED = "approved"
STATUS_RENEWAL_NEEDED = "renewal_needed"
STATUS_SUSPENDED = "suspended"


class InvalidApprovedMonths(ValueError):
    """``file_validity.approved_months`` is not a whole number of months above zero."""


def add_months(moment: datetime, months: int) -> datetime:
    """Move a timezone-aware instant forward by whole calendar months.

    The calendar is the one of ``moment``'s own timezone, so pass a Montreal
    local time: 30 January 22:00 in Montreal is already 31 January in UTC, and
    one month later it would land on 27 February instead of 28 February.
    31 January plus one month is 28 February, or 29 February in a leap year.
    The time of day and the timezone stay as they were.
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
    """Expiry of a file approved at ``approved_at`` (a Montreal local time).

    The rule schema sets the real minimum. This only refuses values that would
    break the date math.
    """
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
    """Expiry stored on a file in this status.

    An approved file lasts until ``approved_until``. A renewal-needed file
    expired ``renewal_overdue_by`` before ``moment``. A suspended file lasts
    ``suspended_for`` after ``moment``. Every other status has no expiry.
    """
    if status == STATUS_RENEWAL_NEEDED:
        return moment - renewal_overdue_by
    if status == STATUS_SUSPENDED:
        return moment + suspended_for
    if status == STATUS_APPROVED:
        return approved_until
    return None
