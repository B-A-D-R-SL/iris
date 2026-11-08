# AI contribution: 50% or more AI-generated
"""US-36: where "today" ends for the pickup-today filter (BR-LIST-005)."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from modules.listings.domain.browsing import end_of_local_day

MONTREAL = ZoneInfo("America/Montreal")


# rule: BR-LIST-005
@pytest.mark.parametrize(
    ("now", "expected"),
    [
        pytest.param(
            datetime(2026, 11, 6, 15, tzinfo=UTC),
            datetime(2026, 11, 7, 5, tzinfo=UTC),
            id="winter-day-ends-at-montreal-midnight",
        ),
        pytest.param(
            datetime(2026, 7, 15, 12, tzinfo=UTC),
            datetime(2026, 7, 16, 4, tzinfo=UTC),
            id="summer-day-ends-at-montreal-midnight",
        ),
        pytest.param(
            # 22:00 on Nov 5 in Montreal is already Nov 6 in UTC.
            datetime(2026, 11, 6, 3, tzinfo=UTC),
            datetime(2026, 11, 6, 5, tzinfo=UTC),
            id="montreal-date-not-utc-date",
        ),
        pytest.param(
            datetime(2026, 11, 7, 4, 59, 59, tzinfo=UTC),
            datetime(2026, 11, 7, 5, tzinfo=UTC),
            id="one-second-before-midnight",
        ),
        pytest.param(
            datetime(2026, 11, 7, 5, tzinfo=UTC),
            datetime(2026, 11, 8, 5, tzinfo=UTC),
            id="at-midnight-a-new-day-starts",
        ),
        pytest.param(
            # Nov 1, 2026: clocks go back at 02:00, so the day lasts 25 hours.
            datetime(2026, 11, 1, 4, 30, tzinfo=UTC),
            datetime(2026, 11, 2, 5, tzinfo=UTC),
            id="daylight-saving-ends",
        ),
        pytest.param(
            # Mar 8, 2026: clocks go forward at 02:00, so the day lasts 23 hours.
            datetime(2026, 3, 8, 6, tzinfo=UTC),
            datetime(2026, 3, 9, 4, tzinfo=UTC),
            id="daylight-saving-starts",
        ),
        pytest.param(
            datetime(2026, 11, 6, 10, tzinfo=MONTREAL),
            datetime(2026, 11, 7, 5, tzinfo=UTC),
            id="clock-already-in-montreal-time",
        ),
    ],
)
def test_today_ends_at_the_next_montreal_midnight(
    now: datetime, expected: datetime
) -> None:
    """Today ends at the next montreal midnight."""
    assert end_of_local_day(now, MONTREAL) == expected


# rule: BR-LIST-005
def test_a_naive_clock_is_refused() -> None:
    """A naive clock is refused."""
    with pytest.raises(ValueError, match="timezone-aware"):
        end_of_local_day(datetime(2026, 11, 6, 10), MONTREAL)  # noqa: DTZ001
