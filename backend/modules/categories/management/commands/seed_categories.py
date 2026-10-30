# AI contribution: 50% or more AI-generated
"""Seed default listing categories without overwriting existing records."""

from pathlib import Path
from typing import Any

import yaml
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.categories.models import Category
from modules.categories.services import get_or_create_category

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "categories.yaml"

REQUIRED_FIELDS = {
    "code",
    "name_fr",
    "name_en",
    "is_food",
    "default_value_cents",
    "is_active",
}


def load_category_data(path: Path) -> list[dict[str, Any]]:
    """Read and validate the structure of the category seed file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CommandError(f"Could not read category data: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("categories"), list):
        raise CommandError("Expected a 'categories' list in the YAML file.")

    rows = data["categories"]
    seen_codes: set[str] = set()

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) != REQUIRED_FIELDS:
            raise CommandError(
                f"Category {index} must contain exactly the required fields."
            )

        if any(
            not isinstance(row[key], str) or not row[key].strip()
            for key in ("code", "name_fr", "name_en")
        ):
            raise CommandError(f"Category {index} has invalid text fields.")

        if (
            type(row["is_food"]) is not bool
            or type(row["is_active"]) is not bool
            or type(row["default_value_cents"]) is not int
        ):
            raise CommandError(f"Category {index} has invalid field types.")

        code = row["code"]

        if code in seen_codes:
            raise CommandError(f"Duplicate category code: {code}")

        seen_codes.add(code)

    return rows


class Command(BaseCommand):
    """Create missing categories while preserving existing records."""

    help = "Seed missing listing categories from the reviewed YAML file."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        """Create categories atomically without overwriting staff edits."""
        rows = load_category_data(SEED_PATH)

        created = 0

        for row in rows:
            try:
                _, was_created = get_or_create_category(Category(**row))
            except ValidationError as exc:
                raise CommandError(f"Invalid category {row['code']}: {exc}") from exc

            created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories: {created} created, "
                f"{len(rows) - created} already existing."
            )
        )
