# AI contribution: 50% or more AI-generated
"""Pickup checks for US-44. Plain values: no Django and no database."""

from datetime import datetime

# Refusal codes. The API returns them as ``code`` so the scan screen can show
# its own French or English text for each one.
UNKNOWN_CODE = "unknown_code"
UNKNOWN_RESERVATION = "unknown_reservation"
WRONG_STORE = "wrong_store"
AMBIGUOUS_CODE = "ambiguous_code"
ALREADY_PICKED_UP = "already_picked_up"
CANCELLED = "cancelled"
NO_SHOW = "no_show"
NOT_OPEN_YET = "not_open_yet"
WINDOW_ENDED = "window_ended"


class PickupRefused(Exception):
    """A lookup or confirmation the store must not act on; ``code`` names the reason.

    ``picked_up_at`` is set only for ``already_picked_up``, so staff can see when
    the goods were handed over the first time.
    """

    def __init__(self, code: str, *, picked_up_at: datetime | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.picked_up_at = picked_up_at


def normalize_code(raw: str) -> str:
    """Uppercase a typed or scanned code and drop its spaces."""
    return "".join(raw.split()).upper()


def window_refusal(
    now: datetime, pickup_start: datetime, pickup_end: datetime
) -> str | None:
    """Refuse a confirmation outside the listing's pickup window (BR-RES-002).

    Both ends are included. Late confirmation of a missed pickup is US-45.
    """
    if any(value.utcoffset() is None for value in (now, pickup_start, pickup_end)):
        raise ValueError("Pickup times must be timezone-aware.")
    if now < pickup_start:
        return NOT_OPEN_YET
    if now > pickup_end:
        return WINDOW_ENDED
    return None
