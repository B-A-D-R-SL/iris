# AI contribution: 50% or more AI-generated
"""Pure business rules for listing categories."""

from datetime import date, timedelta


class BestBeforeDateError(ValueError):
    """Raised when a food listing violates its date requirement."""


def validate_best_before_date(
    *,
    is_food: bool,
    best_before_date: date | None,
    pickup_end_date: date,
    margin_days: int,
) -> None:
    """Validate the best-before date for a listing.

    Food categories require a best-before date at least
    margin_days after the pickup end date.

    Non-food categories do not require a best-before date.

    The caller supplies the configured margin rather than
    the domain rule reading Django settings or the database.
    """
    if margin_days < 0:
        raise ValueError("The best-before margin cannot be negative.")

    if not is_food:
        return

    if best_before_date is None:
        raise BestBeforeDateError("Food categories require a best-before date.")

    minimum_date = pickup_end_date + timedelta(days=margin_days)

    if best_before_date < minimum_date:
        raise BestBeforeDateError(
            "The best-before date must be on or after the minimum permitted date."
        )
