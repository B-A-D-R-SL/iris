# AI contribution: 50% or more AI-generated
"""Tests for the Categories seed management command."""

from io import StringIO

import pytest
import yaml
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.categories.management.commands import seed_categories
from modules.categories.models import Category
from modules.categories.services import get_or_create_category


@pytest.mark.django_db
def test_seed_creates_all_default_categories() -> None:
    """All sixteen reviewed categories should be available."""
    call_command("seed_categories", stdout=StringIO())

    assert Category.objects.count() == 16
    assert Category.objects.filter(code="bakery").exists()
    assert Category.objects.filter(code="hygiene").exists()

    bakery = Category.objects.get(code="bakery")
    assert bakery.is_food is True
    assert bakery.default_value_cents == 400


@pytest.mark.django_db
def test_seed_is_idempotent() -> None:
    """Running the seed twice must not create duplicates."""
    call_command("seed_categories", stdout=StringIO())
    call_command("seed_categories", stdout=StringIO())

    assert Category.objects.count() == 16


@pytest.mark.django_db
def test_seed_preserves_existing_changes() -> None:
    """Do not overwrite names modified by an administrator."""
    call_command("seed_categories", stdout=StringIO())

    bakery = Category.objects.get(code="bakery")
    bakery.name_en = "Custom bakery name"
    bakery.save(update_fields=["name_en"])

    call_command("seed_categories", stdout=StringIO())

    bakery.refresh_from_db()
    assert bakery.name_en == "Custom bakery name"


@pytest.mark.django_db
def test_seed_rolls_back_on_invalid_category(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid seed entries must not leave partially created data."""
    path = tmp_path / "categories.yaml"

    valid = {
        "code": "valid",
        "name_fr": "Valide",
        "name_en": "Valid",
        "is_food": False,
        "default_value_cents": 500,
        "is_active": True,
    }

    invalid = {
        **valid,
        "code": "invalid",
        "default_value_cents": -100,
    }

    path.write_text(
        yaml.safe_dump({"categories": [valid, invalid]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(seed_categories, "SEED_PATH", path)

    with pytest.raises(CommandError, match="Invalid category"):
        call_command("seed_categories", stdout=StringIO())

    assert Category.objects.count() == 0


@pytest.mark.django_db
def test_get_or_create_category_preserves_existing_values() -> None:
    """Repeated creation should return the existing record unchanged."""
    candidate = Category(
        code="bakery",
        name_fr="Boulangerie",
        name_en="Bakery",
        is_food=True,
        default_value_cents=400,
        is_active=True,
    )

    first, created = get_or_create_category(candidate)
    assert created is True

    candidate.name_en = "Changed by seed"
    second, created_again = get_or_create_category(candidate)

    assert created_again is False
    assert second.pk == first.pk
    assert second.name_en == "Bakery"
    assert Category.objects.count() == 1
