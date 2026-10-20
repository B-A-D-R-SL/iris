"""Seed the first version of every supported business-rule type."""

import csv
from copy import deepcopy
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils import timezone

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
    data_directory = settings.BASE_DIR / "modules" / "eligibility" / "data"
    candidates = sorted(data_directory.glob("lico_[0-9][0-9][0-9][0-9].csv"))
    if not candidates:
        raise CommandError(
            "No LICO data file found. Complete SET-08 or pass --lico-file with "
            "a reviewed lico_<year>.csv file."
        )
    return candidates[-1]


def _load_lico_values(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CommandError(f"LICO data file does not exist: {path}")

    try:
        year = int(path.stem.removeprefix("lico_"))
    except ValueError as exc:
        raise CommandError("LICO filename must use the form lico_<year>.csv.") from exc

    thresholds: dict[int, int] = {}
    try:
        with path.open(newline="", encoding="utf-8-sig") as data_file:
            reader = csv.DictReader(data_file)
            if reader.fieldnames != ["family_size", "threshold_cents"]:
                raise CommandError(
                    "LICO CSV headers must be family_size,threshold_cents."
                )
            for line_number, row in enumerate(reader, start=2):
                family_size, threshold_cents = _parse_lico_row(row, line_number)
                if family_size in thresholds:
                    raise CommandError(
                        f"LICO CSV contains family size {family_size} more than once."
                    )
                thresholds[family_size] = threshold_cents
    except OSError as exc:
        raise CommandError(f"Could not read LICO data file {path}: {exc}") from exc

    if set(thresholds) != EXPECTED_LICO_SIZES:
        missing = sorted(EXPECTED_LICO_SIZES - set(thresholds))
        unexpected = sorted(set(thresholds) - EXPECTED_LICO_SIZES)
        raise CommandError(
            "LICO CSV must contain family sizes 1 through 7 exactly once; "
            f"missing={missing}, unexpected={unexpected}."
        )

    return {
        "year": year,
        "source_url": LICO_SOURCE_URL,
        "retrieved_on": timezone.localdate().isoformat(),
        "thresholds": {
            str(family_size): thresholds[family_size]
            for family_size in sorted(thresholds)
        },
    }


def _parse_lico_row(row: dict[str, str], line_number: int) -> tuple[int, int]:
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


def _get_seed_publisher() -> AbstractBaseUser:
    user_model = get_user_model()
    username_field = user_model.USERNAME_FIELD
    publisher, created = user_model._default_manager.get_or_create(
        **{username_field: SEED_USERNAME}  # type: ignore[arg-type]
    )
    if created:
        publisher.set_unusable_password()
        publisher.save(update_fields=["password"])
    return publisher
