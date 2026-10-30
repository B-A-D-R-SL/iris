# AI contribution: 50% or more AI-generated
"""Pure domain tests for the eligibility rule in #459."""

import pytest

from modules.eligibility.domain.eligibility import decide


@pytest.fixture
def thresholds() -> dict[int, int]:
    return {
        1: 12_307,
        2: 24_819,
        3: 36_527,
        4: 45_193,
        5: 59_641,
        6: 68_273,
        7: 83_459,
    }


@pytest.mark.parametrize("household_size", range(1, 8))
@pytest.mark.parametrize(
    ("offset_cents", "eligible"),
    [(-1, True), (0, True), (1, False)],
    ids=["below", "equal", "above"],
)
def test_threshold_boundaries(
    household_size: int,
    offset_cents: int,
    eligible: bool,
    thresholds: dict[int, int],
) -> None:
    threshold_cents = thresholds[household_size]
    income_cents = threshold_cents + offset_cents

    decision = decide(
        household_size=household_size,
        incomes_cents=[income_cents],
        thresholds=thresholds,
    )

    assert decision.eligible is eligible
    assert decision.household_income_cents == income_cents
    assert decision.threshold_cents == threshold_cents
    assert decision.family_size_used == household_size


@pytest.mark.parametrize("household_size", [8, 12])
@pytest.mark.parametrize(
    ("offset_cents", "eligible"),
    [(-1, True), (0, True), (1, False)],
    ids=["below", "equal", "above"],
)
def test_large_households_use_size_seven_threshold(
    household_size: int,
    offset_cents: int,
    eligible: bool,
    thresholds: dict[int, int],
) -> None:
    income_cents = thresholds[7] + offset_cents

    decision = decide(
        household_size=household_size,
        incomes_cents=[income_cents],
        thresholds=thresholds,
    )

    assert decision.eligible is eligible
    assert decision.household_income_cents == income_cents
    assert decision.threshold_cents == thresholds[7]
    assert decision.family_size_used == 7


def test_adult_incomes_are_summed_in_integer_cents(
    thresholds: dict[int, int],
) -> None:
    decision = decide(
        household_size=3,
        incomes_cents=[12_345, 23_456],
        thresholds=thresholds,
    )

    assert decision.eligible is True
    assert decision.household_income_cents == 35_801
    assert type(decision.household_income_cents) is int
    assert decision.threshold_cents == thresholds[3]
    assert decision.family_size_used == 3


@pytest.mark.parametrize(
    ("threshold_cents", "eligible"),
    [(299, False), (301, True)],
)
def test_supplied_threshold_controls_decision(
    threshold_cents: int,
    eligible: bool,
    thresholds: dict[int, int],
) -> None:
    thresholds[1] = threshold_cents

    decision = decide(
        household_size=1,
        incomes_cents=[300],
        thresholds=thresholds,
    )

    assert decision.eligible is eligible
    assert decision.household_income_cents == 300
    assert decision.threshold_cents == threshold_cents
    assert decision.family_size_used == 1
