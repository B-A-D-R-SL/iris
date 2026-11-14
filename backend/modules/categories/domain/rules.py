# AI contribution: 50% or more AI-generated
"""Pure business rules for listing categories."""


class DefaultValueOutOfRange(ValueError):
    """Raised when a category's default value is outside the allowed range."""


def validate_default_value(value_cents: int, *, max_cents: int) -> None:
    """Check a category's default value against the listing value limit.

    The default value stands in for a listing's estimated value, so it follows
    the same range: from 0 to ``max_cents`` (``listing_posting`` rule setting).
    """
    # rule: BR-CAT-001 default value from 0 to the listing value limit.
    if max_cents < 0:
        raise ValueError("The maximum value cannot be negative.")
    if not 0 <= value_cents <= max_cents:
        raise DefaultValueOutOfRange(
            "The default value must be between 0 and the listing value limit."
        )
