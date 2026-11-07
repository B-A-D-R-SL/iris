# AI contribution: 50% or more AI-generated
"""US-44 pure pickup checks: code normalization and the pickup window."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from modules.reservations.domain import pickup
from modules.reservations.domain.pickup import normalize_code, window_refusal

MONTREAL = ZoneInfo("America/Montreal")
START = datetime(2026, 11, 7, 16, tzinfo=MONTREAL)
END = START + timedelta(hours=2)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("abc234", "ABC234"), (" AB C2 34 ", "ABC234"), ("ab\tc2\n34", "ABC234")],
)
def test_us44_code_is_uppercased_without_spaces(raw: str, expected: str) -> None:
    assert normalize_code(raw) == expected


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (START - timedelta(seconds=1), pickup.NOT_OPEN_YET),
        (START, None),
        (START + timedelta(hours=1), None),
        (END, None),
        (END + timedelta(seconds=1), pickup.WINDOW_ENDED),
    ],
)
def test_us44_confirmation_only_inside_the_window(
    now: datetime, expected: str | None
) -> None:
    # rule: BR-RES-002
    assert window_refusal(now, START, END) == expected


def test_us44_window_compares_instants_across_time_zones() -> None:
    # rule: BR-RES-002
    utc_now = (START + timedelta(minutes=5)).astimezone(ZoneInfo("UTC"))
    assert window_refusal(utc_now, START, END) is None


def test_us44_naive_times_are_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        window_refusal(START.replace(tzinfo=None), START, END)


def test_us44_refusal_keeps_first_pickup_time() -> None:
    refused = pickup.PickupRefused(pickup.ALREADY_PICKED_UP, picked_up_at=START)
    assert (refused.code, refused.picked_up_at, str(refused)) == (
        pickup.ALREADY_PICKED_UP,
        START,
        pickup.ALREADY_PICKED_UP,
    )
