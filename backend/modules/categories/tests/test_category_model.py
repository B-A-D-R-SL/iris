# AI contribution: 50% or more AI-generated
"""Database rules of the Category model that listings depend on."""

from pathlib import Path
from typing import cast

import pytest
import yaml
from django.db import IntegrityError

from modules.categories.models import Category
from modules.categories.tests.factories import CategoryFactory

SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "categories.yaml"


@pytest.mark.django_db
def test_factory_builds_a_valid_active_category() -> None:
    category = cast(Category, CategoryFactory())

    category.full_clean()
    assert category.is_active


@pytest.mark.django_db
def test_every_seed_category_fits_the_model() -> None:
    rows = yaml.safe_load(SEED_FILE.read_text(encoding="utf-8"))["categories"]

    assert rows
    for row in rows:
        Category(**row).full_clean()


@pytest.mark.django_db
def test_database_rejects_a_negative_default_value() -> None:
    # PositiveBigIntegerField adds the database check; PostgreSQL names it.
    with pytest.raises(IntegrityError, match="default_value_cents"):
        CategoryFactory(default_value_cents=-1)


@pytest.mark.django_db
def test_database_rejects_a_duplicate_code() -> None:
    CategoryFactory(code="bakery")

    with pytest.raises(IntegrityError):
        CategoryFactory(code="bakery")
