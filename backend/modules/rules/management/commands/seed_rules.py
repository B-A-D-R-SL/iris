# AI contribution: 50% or more AI-generated
"""Seed the first version of every supported business-rule type."""

import csv
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from modules.rules.domain.schemas import DEFAULT_RULE_VALUES, RULE_TYPES
from modules.rules.models import RuleSetVersion
from modules.rules.services import publish

LICO_SOURCE_URL = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1110024101"
EXPECTED_LICO_SIZES = set(range(1, 8))
SEED_USERNAME = "rules-seed@iris.local"


class Command(BaseCommand):
    """Create version 1 for rule types that have not been seeded yet."""

    help = "Create version 1 of every business-rule type without duplicating data."

    def add_arguments(self, parser: CommandParser) -> None:
        """Accept a reviewed LICO CSV path for the initial rule seed."""
        parser.add_argument(
            "--lico-file",
            type=Path,
            help=(
                "Path to SET-08's lico_<year>.csv. By default, the newest file "
                "under modules/eligibility/data is used."
            ),
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        """Publish missing version-one rules together without rewriting existing ones."""
        if set(DEFAULT_RULE_VALUES) != set(RULE_TYPES) - {"lico_thresholds"}:
            raise CommandError("Seed defaults do not cover every supported rule type.")

        versioned_types = set(
            RuleSetVersion.objects.filter(rule_type__in=RULE_TYPES).values_list(
                "rule_type", flat=True
            )
        )
        existing_types = set(
            RuleSetVersion.objects.filter(
                rule_type__in=RULE_TYPES, version=1
            ).values_list("rule_type", flat=True)
        )
        invalid_types = versioned_types - existing_types
        if invalid_types:
            names = ", ".join(sorted(invalid_types))
            raise CommandError(f"Rule types have versions but no version 1: {names}.")

        missing_types = [
            rule_type for rule_type in RULE_TYPES if rule_type not in existing_types
        ]
        if not missing_types:
            _repair_existing_seed_publisher()
            self.stdout.write(self.style.SUCCESS("Rule defaults are already seeded."))
            return

        rule_values = deepcopy(DEFAULT_RULE_VALUES)
        if "lico_thresholds" in missing_types:
            lico_file = options["lico_file"] or _find_latest_lico_file()
            rule_values["lico_thresholds"] = _load_lico_values(lico_file)

        publisher = _get_seed_publisher()
        effective_from = timezone.now()
        for rule_type in missing_types:
            publish(
                rule_type,
                rule_values[rule_type],
                publisher,
                effective_from=effective_from,
            )
            self.stdout.write(f"Created {rule_type} version 1.")

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(missing_types)} rule type(s).")
        )


def _find_latest_lico_file() -> Path:
    """Select the highest-year bundled LICO CSV for an initial seed."""
    data_directory = settings.BASE_DIR / "modules" / "eligibility" / "data"
    candidates = sorted(data_directory.glob("lico_[0-9][0-9][0-9][0-9].csv"))
    if not candidates:
        raise CommandError(
            "No LICO data file found. Complete SET-08 or pass --lico-file with "
            "a reviewed lico_<year>.csv file."
        )
    return candidates[-1]


def _load_lico_values(path: Path) -> dict[str, Any]:
    """Validate source metadata and seven cent amounts before publishing them."""
    if not path.is_file():
        raise CommandError(f"LICO data file does not exist: {path}")

    try:
        year = int(path.stem.removeprefix("lico_"))
    except ValueError as exc:
        raise CommandError("LICO filename must use the form lico_<year>.csv.") from exc

    metadata, thresholds = _read_lico_csv(path)
    retrieved_on = _validate_lico_metadata(metadata)
    _validate_lico_sizes(thresholds)

    return {
        "year": year,
        "source_url": metadata["source_url"],
        "retrieved_on": retrieved_on,
        "thresholds": {
            str(family_size): thresholds[family_size]
            for family_size in sorted(thresholds)
        },
    }


def _read_lico_csv(path: Path) -> tuple[dict[str, str], dict[int, int]]:
    """Read source metadata and parse the threshold rows."""
    metadata: dict[str, str] = {}
    try:
        with path.open(newline="", encoding="utf-8-sig") as data_file:
            csv_lines: list[str] = []
            comment_line_count = 0
            for line in data_file:
                if not csv_lines and line.startswith("#"):
                    comment_line_count += 1
                    key, separator, value = line[1:].partition(":")
                    key = key.strip()
                    if separator and key in {"source_url", "retrieved_on"}:
                        if key in metadata:
                            raise CommandError(f"LICO CSV repeats {key} metadata.")
                        metadata[key] = value.strip()
                    continue
                csv_lines.append(line)
        return metadata, _parse_lico_rows(csv_lines, comment_line_count)
    except OSError as exc:
        raise CommandError(f"Could not read LICO data file {path}: {exc}") from exc


def _parse_lico_rows(lines: list[str], comment_line_count: int) -> dict[int, int]:
    """Validate CSV columns and reject repeated family sizes."""
    reader = csv.DictReader(lines)
    if reader.fieldnames != ["family_size", "threshold_cents"]:
        raise CommandError("LICO CSV headers must be family_size,threshold_cents.")
    thresholds: dict[int, int] = {}
    for line_number, row in enumerate(reader, start=comment_line_count + 2):
        if None in row:
            raise CommandError(
                f"LICO CSV line {line_number} must have exactly two columns."
            )
        family_size, threshold_cents = _parse_lico_row(row, line_number)
        if family_size in thresholds:
            raise CommandError(
                f"LICO CSV contains family size {family_size} more than once."
            )
        thresholds[family_size] = threshold_cents
    return thresholds


def _validate_lico_metadata(metadata: dict[str, str]) -> str:
    """Require the reviewed source and a canonical retrieval date."""
    if metadata.get("source_url") != LICO_SOURCE_URL:
        raise CommandError(f"LICO CSV source_url must be {LICO_SOURCE_URL}.")
    retrieved_on = metadata.get("retrieved_on", "")
    try:
        if date.fromisoformat(retrieved_on).isoformat() != retrieved_on:
            raise ValueError("retrieved_on must use YYYY-MM-DD")
    except ValueError as exc:
        raise CommandError(
            "LICO CSV retrieved_on must use an ISO date (YYYY-MM-DD)."
        ) from exc
    return retrieved_on


def _validate_lico_sizes(thresholds: dict[int, int]) -> None:
    """Require one threshold for each supported family size."""
    if set(thresholds) != EXPECTED_LICO_SIZES:
        missing = sorted(EXPECTED_LICO_SIZES - set(thresholds))
        unexpected = sorted(set(thresholds) - EXPECTED_LICO_SIZES)
        raise CommandError(
            "LICO CSV must contain family sizes 1 through 7 exactly once; "
            f"missing={missing}, unexpected={unexpected}."
        )


def _parse_lico_row(row: dict[str, str], line_number: int) -> tuple[int, int]:
    """Parse one family-size row and require a positive integer cent amount."""
    try:
        family_size = int(row["family_size"])
        threshold_cents = int(row["threshold_cents"])
    except (TypeError, ValueError) as exc:
        raise CommandError(
            f"LICO CSV line {line_number} must contain integer values."
        ) from exc
    if threshold_cents <= 0:
        raise CommandError(
            f"LICO CSV line {line_number} threshold_cents must be positive."
        )
    return family_size, threshold_cents


def _repair_existing_seed_publisher() -> None:
    """Repair an existing system account when all rule types are already seeded."""
    user_model = get_user_model()
    if user_model._default_manager.filter(
        **{user_model.USERNAME_FIELD: SEED_USERNAME}
    ).exists():
        _get_seed_publisher()


def _get_seed_publisher() -> AbstractBaseUser:
    """Get the seed audit account, creating it without a usable password."""
    user_model = get_user_model()
    username_field = user_model.USERNAME_FIELD
    publisher, created = user_model._default_manager.get_or_create(
        defaults={"role": "admin"},
        **{username_field: SEED_USERNAME},  # type: ignore[arg-type]
    )
    if created:
        publisher.set_unusable_password()
        publisher.save(update_fields=["password"])
    elif publisher.has_usable_password() or getattr(publisher, "store_id", None):
        raise CommandError(
            _("The rules seed account must be a non-login system account.")
        )
    elif getattr(publisher, "role", None) == "beneficiary":
        publisher.role = "admin"  # type: ignore[attr-defined]
        publisher.save(update_fields=["role"])
    elif getattr(publisher, "role", None) != "admin":
        raise CommandError(_("The rules seed account has an unexpected role."))
    return publisher
