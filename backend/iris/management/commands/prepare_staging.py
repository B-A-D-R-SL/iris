# AI contribution: 50% or more AI-generated
"""Serialize migrations and the existing fictional seed across container restarts."""

import logging
import os
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from iris.startup_messages import operator_gettext as _

logger = logging.getLogger("iris.deployment")
# Fixed infrastructure lock, unrelated to domain RuleSet business values.
STAGING_SETUP_LOCK = 408_017


def _seed_option() -> bool:
    if settings.SETTINGS_MODULE != "iris.settings.staging":
        raise CommandError(_("prepare_staging requires iris.settings.staging."))
    seed = os.environ.get("IRIS_SEED_ON_START", "0")
    if seed not in {"0", "1"}:
        raise CommandError(_("IRIS_SEED_ON_START must be 0 or 1."))
    if seed == "1" and not os.environ.get("SEED_PASSWORD", "").strip():
        raise CommandError(_("SEED_PASSWORD is required before staging setup."))
    return seed == "1"


def _prepare_database(seed: bool) -> None:
    call_command("check", deploy=True, fail_level="WARNING")
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [STAGING_SETUP_LOCK])
        try:
            call_command("migrate", interactive=False)
            logger.info(
                "staging_migrations_completed",
                extra={"event": "staging_migrations_completed"},
            )
            if seed:
                call_command("seed")
                logger.info(
                    "staging_seed_completed", extra={"event": "staging_seed_completed"}
                )
        finally:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [STAGING_SETUP_LOCK])


class Command(BaseCommand):
    # argparse requires a concrete string; our catalog loader is registry-safe.
    help = str(
        _("Migrate and optionally seed fictional staging under a PostgreSQL lock.")
    )

    def handle(self, *args: Any, **options: Any) -> None:
        logger.info("staging_setup_started", extra={"event": "staging_setup_started"})
        try:
            seed = _seed_option()
        except CommandError:
            logger.error(
                "staging_setup_failed", extra={"event": "staging_setup_failed"}
            )
            raise
        try:
            _prepare_database(seed)
        except Exception:  # noqa: BLE001 - DB/seed exceptions can contain configuration.
            logger.error(
                "staging_setup_failed", extra={"event": "staging_setup_failed"}
            )
            raise CommandError(
                _(
                    "Staging setup failed; check configuration and database availability."
                )
            ) from None
        logger.info(
            "staging_setup_completed", extra={"event": "staging_setup_completed"}
        )
