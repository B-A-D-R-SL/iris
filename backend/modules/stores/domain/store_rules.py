# AI contribution: 50% or more AI-generated
"""Store administration rules (US-14). Plain values: no Django, no database.

Opening hours are one time range per day, or ``None`` when the store is
closed that day::

    {"mon": {"open": "08:00", "close": "20:00"}, ..., "sun": None}

A free-text ``notes`` value copied from a partner application may sit next to
the days; it is kept as it is and never edited here.
"""

import re
from collections.abc import Mapping

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
NOTES_KEY = "notes"
REASON_MAX_LENGTH = 500

# Error codes; the service turns them into translated messages.
HOURS_NOT_A_WEEK = "hours_not_a_week"
HOURS_INVALID_TIME = "hours_invalid_time"
HOURS_CLOSE_BEFORE_OPEN = "hours_close_before_open"
HOURS_NO_OPEN_DAY = "hours_no_open_day"
REASON_REQUIRED = "reason_required"
REASON_TOO_LONG = "reason_too_long"

_TIME = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


def _day_error(value: object) -> str | None:
    """None when the day is closed or a valid range, else an error code."""
    if value is None:
        return None
    if not isinstance(value, Mapping) or set(value) != {"open", "close"}:
        return HOURS_INVALID_TIME
    opens, closes = value["open"], value["close"]
    if not all(isinstance(t, str) and _TIME.fullmatch(t) for t in (opens, closes)):
        return HOURS_INVALID_TIME
    # Zero-padded "HH:MM" strings compare in time order.
    if closes <= opens:
        return HOURS_CLOSE_BEFORE_OPEN
    return None


def weekly_hours_errors(value: object) -> dict[str, str]:
    """Error codes by day (or ``week``); empty when the schedule is valid.

    rule: BR-STORE-006 seven days, one range each or closed, close after open,
    and at least one open day.
    """
    if not isinstance(value, Mapping) or not set(DAYS) <= set(value):
        return {"week": HOURS_NOT_A_WEEK}
    if set(value) - {*DAYS, NOTES_KEY}:
        return {"week": HOURS_NOT_A_WEEK}
    errors = {day: code for day in DAYS if (code := _day_error(value[day]))}
    if not errors and all(value[day] is None for day in DAYS):
        errors["week"] = HOURS_NO_OPEN_DAY
    return errors


def schedule_with_notes(
    new: Mapping[str, object], current: object
) -> dict[str, object]:
    """The submitted days, keeping any existing free-text notes untouched."""
    schedule: dict[str, object] = {day: new[day] for day in DAYS}
    if isinstance(current, Mapping) and isinstance(current.get(NOTES_KEY), str):
        schedule[NOTES_KEY] = current[NOTES_KEY]
    return schedule


def clean_reason(reason: object) -> tuple[str, str | None]:
    """The trimmed reason and an error code, if any (BR-STORE-005)."""
    if not isinstance(reason, str) or not reason.strip():
        return "", REASON_REQUIRED
    trimmed = reason.strip()
    if len(trimmed) > REASON_MAX_LENGTH:
        return trimmed, REASON_TOO_LONG
    return trimmed, None


def changed_fields(
    before: Mapping[str, object], after: Mapping[str, object]
) -> list[str]:
    """Sorted names of the fields whose value differs (audit metadata)."""
    return sorted(field for field in after if before.get(field) != after[field])
