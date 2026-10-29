# AI contribution: 50% or more AI-generated
"""Tests for Category services and queries."""

import pytest
from django.core.exceptions import ValidationError

from modules.categories.models import Category
from modules.categories.queries import (
    get_active_category,
    list_active_categories,
)
from modules.categories.services import (
    deactivate_category,
    save_category,
)


def make_category(
    code: str = "bakery",
    *,
    is_active: bool = True,
) -> Category:
    """Build an unsaved category for testing."""
    return Category(
        code=code,
        name_fr="Boulangerie",
        name_en="Bakery",
        is_food=True,
        default_value_cents=400,
        is_active=is_active,
    )


@pytest.mark.django_db
def test_save_category_creates_record() -> None:
    category = make_category()

    saved = save_category(category)

    assert saved.pk is not None
    assert Category.objects.filter(pk=saved.pk).exists()
    assert saved.default_value_cents == 400


@pytest.mark.django_db
def test_save_category_allows_name_update() -> None:
    category = save_category(make_category())

    category.name_en = "Baked goods"
    save_category(category)

    category.refresh_from_db()
    assert category.name_en == "Baked goods"


@pytest.mark.django_db
def test_category_code_cannot_change() -> None:
    category = save_category(make_category())

    category.code = "different_code"

    with pytest.raises(ValidationError, match="cannot be changed"):
        save_category(category)

    category.refresh_from_db()
    assert category.code == "bakery"


@pytest.mark.django_db
def test_save_category_rejects_invalid_data() -> None:
    category = make_category()
    category.name_fr = ""

    with pytest.raises(ValidationError):
        save_category(category)

    assert Category.objects.count() == 0


@pytest.mark.django_db
def test_deactivate_category() -> None:
    category = save_category(make_category())

    deactivated = deactivate_category(category.pk)

    assert deactivated.is_active is False

    category.refresh_from_db()
    assert category.is_active is False


@pytest.mark.django_db
def test_list_active_categories_excludes_inactive() -> None:
    save_category(make_category("bakery"))
    save_category(make_category("clothing"))
    save_category(make_category("inactive", is_active=False))

    result = list(list_active_categories())

    assert [category.code for category in result] == [
        "bakery",
        "clothing",
    ]


@pytest.mark.django_db
def test_get_active_category() -> None:
    save_category(make_category())

    result = get_active_category("bakery")

    assert result.code == "bakery"
    assert result.is_active is True


@pytest.mark.django_db
def test_get_active_category_rejects_inactive() -> None:
    save_category(make_category(is_active=False))

    with pytest.raises(Category.DoesNotExist):
        get_active_category("bakery")


@pytest.mark.django_db
def test_get_active_category_rejects_unknown() -> None:
    with pytest.raises(Category.DoesNotExist):
        get_active_category("unknown")
