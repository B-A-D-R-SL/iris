# AI contribution: 50% or more AI-generated
"""Serialize migrations and the existing fictional seed across container restarts."""

import os
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

# Fixed infrastructure lock, unrelated to domain RuleSet business values.
STAGING_SETUP_LOCK = 408_017


class Command(BaseCommand):
    help = "Migrate and optionally seed fictional staging under a PostgreSQL lock."

    def handle(self, *args: Any, **options: Any) -> None:
        if settings.SETTINGS_MODULE != "iris.settings.staging":
            raise CommandError("prepare_staging requires iris.settings.staging.")
        seed = os.environ.get("IRIS_SEED_ON_START", "0")
        if seed not in {"0", "1"}:
            raise CommandError("IRIS_SEED_ON_START must be 0 or 1.")
        if seed == "1" and not os.environ.get("SEED_PASSWORD", "").strip():
            raise CommandError("SEED_PASSWORD is required before staging setup.")
        call_command("check", deploy=True, fail_level="WARNING")
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", [STAGING_SETUP_LOCK])
            try:
                call_command("migrate", interactive=False)
                if seed == "1":
                    call_command("seed")
            finally:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [STAGING_SETUP_LOCK])
