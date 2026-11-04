# AI contribution: 50% or more AI-generated
"""Validated write operations for listing categories."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from modules.categories.domain.rules import (
    DefaultValueOutOfRange,
    validate_default_value,
)
from modules.categories.models import Category
from modules.rules import queries as rule_queries

# Fields an admin may set; the code only on creation.
EDITABLE_FIELDS = frozenset(
    ("name_fr", "name_en", "is_food", "default_value_cents", "is_active")
)


class CategoryRulesUnavailable(Exception):
    """The listing_posting rule setting (value limit) has not been published."""


def _require_admin(user: AbstractBaseUser) -> None:
    if (
        not user.is_authenticated
        or not user.is_active
        or getattr(user, "role", None) != "admin"
    ):
        raise PermissionDenied(_("Only admins can manage categories."))


def _check_default_value(value_cents: int) -> None:
    """The default value follows the listing value range from the rule settings."""
    posting_rules = rule_queries.active("listing_posting")
    if posting_rules is None:
        raise CategoryRulesUnavailable
    max_cents = int(posting_rules.values["estimated_value_max_cents"])
    try:
        validate_default_value(value_cents, max_cents=max_cents)
    except DefaultValueOutOfRange as exc:
        raise ValidationError(
            {
                "default_value_cents": _("Enter a value from 0 to %(max)s cents.")
                % {"max": max_cents}
            }
        ) from exc


@transaction.atomic
def create_category(values: Mapping[str, Any], admin: AbstractBaseUser) -> Category:
    """Add a category (US-35). New categories are active unless stated otherwise."""
    _require_admin(admin)
    code = values["code"]
    duplicate = ValidationError({"code": _("This category code already exists.")})
    if Category.objects.filter(code=code).exists():
        raise duplicate
    _check_default_value(values["default_value_cents"])
    category = Category(
        code=code, **{field: values[field] for field in EDITABLE_FIELDS & values.keys()}
    )
    try:
        return save_category(category)
    except IntegrityError:
        # Another admin added the same code at the same moment. save_category's
        # savepoint has rolled back, so the check can run; other errors still raise.
        if Category.objects.filter(code=code).exists():
            raise duplicate from None
        raise


@transaction.atomic
def update_category(
    code: str, values: Mapping[str, Any], admin: AbstractBaseUser
) -> Category:
    """Rename, change food or default value, deactivate or reactivate (US-35).

    There is no delete: a category in use keeps its code, and deactivating it
    hides it from the posting and partner forms. Raises Category.DoesNotExist.
    """
    _require_admin(admin)
    if "code" in values:
        raise ValidationError({"code": _("A category code cannot be changed.")})
    category = Category.objects.select_for_update().get(code=code)
    previous_value = category.default_value_cents
    for field in EDITABLE_FIELDS & values.keys():
        setattr(category, field, values[field])
    # The screen sends the value on every edit; check it only when it changes,
    # so a later, lower limit does not block renaming an older category.
    if category.default_value_cents != previous_value:
        _check_default_value(category.default_value_cents)
    return save_category(category)


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


@transaction.atomic
def get_or_create_category(category: Category) -> tuple[Category, bool]:
    """Validate and create a category, safely handling concurrent seeds."""
    category.full_clean(validate_unique=False)
    return Category.objects.get_or_create(
        code=category.code,
        defaults={
            "name_fr": category.name_fr,
            "name_en": category.name_en,
            "is_food": category.is_food,
            "default_value_cents": category.default_value_cents,
            "is_active": category.is_active,
        },
    )
