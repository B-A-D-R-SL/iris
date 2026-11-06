# AI contribution: 50% or more AI-generated
"""US-36 browsing rule that needs no database: where "today" ends."""

from datetime import datetime, time, timedelta, tzinfo


def end_of_local_day(now: datetime, local_tz: tzinfo) -> datetime:
    """The next midnight in ``local_tz`` after ``now``: the end of "today".

    The "pickup today" filter keeps visible listings whose pickup starts
    before this moment. Visible listings have not ended yet, so each one can
    be picked up at some point during the rest of the day, including a window
    that started last night. Midnight comes from the local calendar, so a day
    with a daylight-saving change is 23 or 25 hours long.
    """
    if now.utcoffset() is None:
        raise ValueError("The supplied clock must be timezone-aware.")
    tomorrow = now.astimezone(local_tz).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=local_tz)
