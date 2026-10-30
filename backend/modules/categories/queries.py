# AI contribution: 50% or more AI-generated
"""Read-only access to listing categories."""

from typing import Any
from uuid import UUID

from django.db.models import QuerySet

from modules.categories.models import Category


def list_active_categories() -> QuerySet[Category]:
    """Return active categories ordered by their stable codes."""
    return Category.objects.filter(is_active=True).order_by("code")


def get_active_category(code: str) -> Category:
    """Return an active category by its stable code.

    Raises Category.DoesNotExist when the category is missing
    or inactive.
    """
    return Category.objects.get(code=code, is_active=True)


def for_listing_post(category_id: UUID) -> dict[str, Any] | None:
    """Return a locked category snapshot suitable for pure safety rules."""
    result = (
        Category.objects.select_for_update()
        .filter(pk=category_id)
        .values("id", "code", "is_food", "is_active", "default_value_cents")
        .first()
    )
    return dict(result) if result is not None else None
