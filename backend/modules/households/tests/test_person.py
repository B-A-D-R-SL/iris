# AI contribution: 50% or more AI-generated
"""Adult rule used for notices, BR-DOC-007 (T-03.18.2)."""

from datetime import date

import pytest

from modules.households.domain.person import is_adult


@pytest.mark.parametrize(
    ("birth", "adult"),
    [
        (date(2008, 11, 6), True),  # 18th birthday today
        (date(2008, 11, 7), False),  # one day short
        (date(1950, 1, 1), True),
    ],
)
def test_br_doc_007_is_adult_boundary(birth: date, adult: bool) -> None:
    assert is_adult(birth, date(2026, 11, 6)) is adult
