# AI contribution: 50% or more AI-generated
import pytest

from modules.households.domain.notice_name import notice_name_matches


@pytest.mark.parametrize(
    ("first", "last", "notice", "expected"),
    [
        ("Élodie", "Côté", "elodie Marie COTE", True),
        ("Jean-Luc", "D’Amour", "JEAN LUC D'AMOUR", True),
        ("Ann", "Lee", "Joanne Lee", False),
        ("Example", "Person", "Different Person", False),
        ("Example", "Person", "Example Different", False),
        ("Anne", "Anne", "Anne", False),
        ("Ann", "Lee", "Ann Lee Smith", False),
        ("Ann", "Lee", "Joanne Ann Lee", False),
        ("", "", "", False),
    ],
)
def test_notice_name_comparison(
    first: str, last: str, notice: str, expected: bool
) -> None:
    assert notice_name_matches(first, last, notice) is expected
