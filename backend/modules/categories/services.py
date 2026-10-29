# AI contribution: 50% or more AI-generated
"""Validated write operations for listing categories."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from modules.categories.models import Category


@transaction.atomic
def save_category(category: Category) -> Category:
    """Validate and save a category.

    Category codes are immutable after creation because other
    modules use them as stable identifiers.
    """
    if not category._state.adding:
        existing_code = (
            Category.objects.select_for_update()
            .filter(pk=category.pk)
            .values_list("code", flat=True)
            .first()
        )

        if existing_code is not None and existing_code != category.code:
            raise ValidationError(
                {"code": "Category codes cannot be changed after creation."}
            )

    category.full_clean()
    category.save()

    return category


@transaction.atomic
def deactivate_category(category_id: UUID) -> Category:
    """Deactivate a category without deleting historical records.

    Inactive categories are excluded from public queries.
    """
    category = Category.objects.select_for_update().get(pk=category_id)

    category.is_active = False

    return save_category(category)
