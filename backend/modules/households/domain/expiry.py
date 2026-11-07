# AI contribution: 50% or more AI-generated
"""When a household file expires. Plain dates, no database and no Django.

US-18's approval service and the seed command both call these functions, so
the length of an approved file lives in one place.
"""

import calendar
from datetime import datetime, timedelta

MINIMUM_APPROVED_MONTHS = 1
RENEWAL_ALREADY_DUE = timedelta(days=1)

STATUS_APPROVED = "approved"
STATUS_RENEWAL_NEEDED = "renewal_needed"
STATUS_SUSPENDED = "suspended"


def add_months(moment: datetime, months: int) -> datetime:
    """Move a timezone-aware instant forward by whole calendar months.

    31 January plus one month is 28 February, or 29 February in a leap year.
    The time of day and the timezone stay as they were.
    """
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(moment.day, last_day)
    return moment.replace(year=year, month=month, day=day)


def approved_expiry(moment: datetime, approved_months: object) -> datetime:
    """Expiry of a file approved at ``moment``, using ``file_validity.approved_months``."""
    if type(approved_months) is not int or approved_months < MINIMUM_APPROVED_MONTHS:
        raise ValueError("approved_months must be a positive integer.")
    return add_months(moment, approved_months)


def expiry_for_status(
    status: str,
    moment: datetime,
    approved_until: datetime,
    suspended_for: timedelta,
) -> datetime | None:
    """Expiry stored on a file in this status.

    An approved file lasts until ``approved_until``. A renewal-needed file is
    already one day past ``moment``. A suspended file lasts ``suspended_for``.
    Every other status has no expiry.
    """
    if status == STATUS_RENEWAL_NEEDED:
        return moment - RENEWAL_ALREADY_DUE
    if status == STATUS_SUSPENDED:
        return moment + suspended_for
    if status == STATUS_APPROVED:
        return approved_until
    return None
