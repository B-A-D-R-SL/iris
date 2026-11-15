# AI contribution: 50% or more AI-generated
"""Name comparison for notice review."""

import re

from .address import _fold


def notice_name_matches(first_name: str, last_name: str, notice_name: str) -> bool:
    def tokens(value: str) -> list[str]:
        return re.findall(r"[^\W\d_]+", _fold(value))

    first, last, recorded = tokens(first_name), tokens(last_name), tokens(notice_name)
    # Only extra middle names are allowed; both ends must still match whole tokens.
    return bool(first and last) and (
        len(recorded) >= len(first) + len(last)
        and recorded[: len(first)] == first
        and recorded[-len(last) :] == last
    )
