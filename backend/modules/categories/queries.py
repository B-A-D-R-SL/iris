# AI contribution: 50% or more AI-generated
"""Public category reads for listing creation."""

from typing import Any
from uuid import UUID

from modules.categories.models import Category


def for_listing_post(category_id: UUID) -> dict[str, Any] | None:
    """Return a locked category snapshot suitable for pure safety rules."""
    result = (
        Category.objects.select_for_update()
        .filter(pk=category_id)
        .values("id", "code", "is_food", "is_active", "default_value_cents")
        .first()
    )
    return dict(result) if result is not None else None
