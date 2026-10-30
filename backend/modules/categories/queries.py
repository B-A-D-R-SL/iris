# AI contribution: 50% or more AI-generated
"""Read-only access to listing categories."""

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
