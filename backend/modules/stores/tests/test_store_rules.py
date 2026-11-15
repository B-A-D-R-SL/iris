# AI contribution: 50% or more AI-generated
"""Pure store administration rules (US-14)."""

from typing import Any

import pytest

from modules.stores.domain import store_rules as rules

OPEN = {"open": "08:00", "close": "20:00"}


def _week(**days: Any) -> dict[str, Any]:
    return {day: OPEN for day in rules.DAYS} | days


# rule: BR-STORE-006
def test_a_full_week_with_closed_days_is_valid() -> None:
    assert (
        rules.weekly_hours_errors(
            _week(sun=None, sat={"open": "09:00", "close": "18:00"})
        )
        == {}
    )


def test_notes_may_sit_next_to_the_days() -> None:
    assert rules.weekly_hours_errors(_week(notes="Lun-ven 8h-20h")) == {}


@pytest.mark.parametrize(
    "value",
    [None, [], "8 to 8", {}, {"mon": OPEN}, _week(holiday=None)],
)
def test_anything_but_a_week_is_refused(value: Any) -> None:
    assert rules.weekly_hours_errors(value) == {"week": rules.HOURS_NOT_A_WEEK}


@pytest.mark.parametrize(
    "day",
    [
        {"open": "8:00", "close": "20:00"},
        {"open": "24:00", "close": "23:00"},
        {"open": "08:60", "close": "20:00"},
        {"open": "08:00"},
        {"open": "08:00", "close": "20:00", "note": "x"},
        {"open": 8, "close": 20},
        "08:00-20:00",
    ],
)
def test_invalid_times_are_refused_per_day(day: Any) -> None:
    assert rules.weekly_hours_errors(_week(tue=day)) == {
        "tue": rules.HOURS_INVALID_TIME
    }


@pytest.mark.parametrize("close", ["08:00", "07:59"])
def test_closing_must_come_after_opening(close: str) -> None:
    errors = rules.weekly_hours_errors(_week(fri={"open": "08:00", "close": close}))
    assert errors == {"fri": rules.HOURS_CLOSE_BEFORE_OPEN}


def test_a_week_with_no_open_day_is_refused() -> None:
    week = {day: None for day in rules.DAYS}
    assert rules.weekly_hours_errors(week) == {"week": rules.HOURS_NO_OPEN_DAY}


def test_schedule_keeps_existing_notes_only() -> None:
    new = _week(notes="replaced?")
    assert rules.schedule_with_notes(new, {"notes": "Original"})["notes"] == "Original"
    assert "notes" not in rules.schedule_with_notes(new, {})
    assert "notes" not in rules.schedule_with_notes(new, {"notes": 3})


# rule: BR-STORE-005
@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("  Closed for renovations ", ("Closed for renovations", None)),
        ("x" * 500, ("x" * 500, None)),
        ("x" * 501, ("x" * 501, rules.REASON_TOO_LONG)),
        ("   ", ("", rules.REASON_REQUIRED)),
        (None, ("", rules.REASON_REQUIRED)),
    ],
)
def test_clean_reason(reason: Any, expected: tuple[str, str | None]) -> None:
    assert rules.clean_reason(reason) == expected


def test_changed_fields_lists_differences_in_order() -> None:
    before = {"phone": "+15145550100", "city": "Montréal", "name": "A"}
    after = {"phone": "+15145550199", "name": "A", "city": "Laval"}
    assert rules.changed_fields(before, after) == ["city", "phone"]


# rule: BR-STORE-006
def test_times_need_ascii_digits() -> None:
    """An Arabic-Indic 8 ("0٨:00") must not pass as a closing time."""
    errors = rules.weekly_hours_errors(_week(mon={"open": "09:00", "close": "0٨:00"}))
    assert errors == {"mon": rules.HOURS_INVALID_TIME}
