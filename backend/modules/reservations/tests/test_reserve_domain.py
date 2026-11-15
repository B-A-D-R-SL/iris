# AI contribution: 50% or more AI-generated
"""US-41 rules with no database: pickup codes and household limits."""

import secrets
from collections.abc import Sequence
from itertools import cycle

import pytest

from modules.reservations.domain.codes import (
    PICKUP_CODE_ALPHABET,
    PICKUP_CODE_LENGTH,
    new_pickup_code,
)
from modules.reservations.domain.limits import (
    QUANTITY_OVER_LISTING_LIMIT,
    TOO_MANY_ACTIVE_RESERVATIONS,
    Holding,
    ReservationRulesInvalid,
    read_max_active,
    refusals,
)


# rule: BR-RES-010
def test_pickup_code_has_six_characters_from_the_alphabet() -> None:
    for _ in range(200):
        code = new_pickup_code(secrets.choice)
        assert len(code) == PICKUP_CODE_LENGTH == 6
        assert set(code) <= set(PICKUP_CODE_ALPHABET)


# rule: BR-RES-010
def test_pickup_alphabet_has_no_look_alike_characters() -> None:
    assert not set("ILO01") & set(PICKUP_CODE_ALPHABET)
    assert len(PICKUP_CODE_ALPHABET) == 31


def test_pickup_code_uses_the_chooser_it_is_given() -> None:
    letters = cycle("AB")

    def choose(_alphabet: Sequence[str]) -> str:
        return next(letters)

    assert new_pickup_code(choose) == "ABABAB"


@pytest.mark.parametrize("bad", ["0", "", "AB"])
def test_pickup_code_refuses_a_chooser_outside_the_alphabet(bad: str) -> None:
    with pytest.raises(ValueError, match="alphabet"):
        new_pickup_code(lambda _alphabet: bad)


# rule: BR-RES-007 and BR-RES-008, with a listing max of 2 and a limit of 3.
@pytest.mark.parametrize(
    ("quantity", "active", "on_listing", "expected"),
    [
        (1, 0, 0, []),
        (2, 0, 0, []),  # exactly the listing max
        (3, 0, 0, [QUANTITY_OVER_LISTING_LIMIT]),
        (1, 1, 1, []),  # 1 held + 1 more = 2, the max
        (2, 1, 1, [QUANTITY_OVER_LISTING_LIMIT]),  # in total, not per tap
        (1, 2, 0, []),  # a third active reservation is allowed
        (1, 3, 0, [TOO_MANY_ACTIVE_RESERVATIONS]),  # a fourth is not
        (3, 3, 0, [TOO_MANY_ACTIVE_RESERVATIONS, QUANTITY_OVER_LISTING_LIMIT]),
    ],
)
def test_household_limits(
    quantity: int, active: int, on_listing: int, expected: list[str]
) -> None:
    holding = Holding(active_reservations=active, quantity_on_listing=on_listing)
    assert refusals(quantity, holding, max_per_household=2, max_active=3) == expected


def test_limits_refuse_a_quantity_below_one() -> None:
    with pytest.raises(ValueError):
        refusals(0, Holding(0, 0), max_per_household=2, max_active=3)


def test_max_active_is_read_from_the_rule_values() -> None:
    assert read_max_active({"max_active_per_household": 5}) == 5


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"max_active_per_household": 0},
        {"max_active_per_household": "3"},
        {"max_active_per_household": True},
        {"max_active_per_household": 2.5},
    ],
)
def test_unusable_max_active_is_refused(values: dict[str, object]) -> None:
    with pytest.raises(ReservationRulesInvalid):
        read_max_active(values)
