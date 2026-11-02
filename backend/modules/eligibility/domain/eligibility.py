# AI contribution: 50% or more AI-generated
"""Framework-independent, deterministic household eligibility rule."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Decision:
    """Result of comparing household income with the applicable LICO threshold."""

    eligible: bool
    household_income_cents: int
    threshold_cents: int
    family_size_used: int


def decide(
    household_size: int,
    incomes_cents: list[int],
    thresholds: dict[int, int],
) -> Decision:
    """Determine eligibility using accepted adult incomes and LICO thresholds.

    Household sizes of seven or more share the size-seven threshold.
    Amounts must be integer cents. The caller is responsible for
    selecting adults and confirming their income evidence.
    """
    if type(household_size) is not int or household_size < 1:
        raise ValueError("Household size must be a positive integer.")

    if not isinstance(incomes_cents, list) or not incomes_cents:
        raise ValueError("At least one adult income is required.")

    if len(incomes_cents) > household_size:
        raise ValueError("Adult count cannot exceed household size.")

    if any(type(amount) is not int or amount < 0 for amount in incomes_cents):
        raise ValueError("Adult incomes must be nonnegative integer cents.")

    if not isinstance(thresholds, dict):
        raise TypeError("Thresholds must be a dictionary.")

    family_size_used = min(household_size, 7)

    try:
        threshold_cents = thresholds[family_size_used]
    except KeyError as exc:
        raise ValueError("Missing threshold for household size.") from exc

    if type(threshold_cents) is not int or threshold_cents <= 0:
        raise ValueError("Threshold must be positive integer cents.")

    household_income_cents = sum(incomes_cents)

    return Decision(
        eligible=household_income_cents <= threshold_cents,
        household_income_cents=household_income_cents,
        threshold_cents=threshold_cents,
        family_size_used=family_size_used,
    )
