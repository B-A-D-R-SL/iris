# AI contribution: 50% or more AI-generated
"""The search migration backfills derived keys and reverses without losing files."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)
BEFORE_SEARCH = [("households", "0003_household_consent")]


def _migrate(target):
    """Apply a migration target and return its historical model registry."""
    executor = MigrationExecutor(connection)
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def test_existing_households_and_members_survive_search_upgrade_and_reverse():
    """Preserve source records and backfill searchable keys across a round trip."""
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        old = _migrate(BEFORE_SEARCH)
        file = old.get_model("households", "Household").objects.create(
            phone="+15145550123",
            email="EXEMPLE@EXAMPLE.TEST",
            street_number="123",
            street_name="rue Émile",
            city="Montréal",
            postal_code="H0H 0H0",
            address_key="123|R EMILE||H0H0H0",
        )
        member = old.get_model("households", "Member").objects.create(
            household=file,
            first_name="Élodie",
            last_name="Exemple",
            date_of_birth="1990-01-01",
            relation="holder",
            person_key="EXEMPLE|ELODIE|1990-01-01",
        )
        current = _migrate(latest)
        migrated = current.get_model("households", "Household").objects.get(pk=file.pk)
        holder = current.get_model("households", "Member").objects.get(pk=member.pk)
        assert migrated.search_email_key == "exemple@example.test"
        assert "rue emile" in migrated.search_address_text
        assert holder.search_name_key == "exemple elodie"
        restored = _migrate(BEFORE_SEARCH)
        original = restored.get_model("households", "Household").objects.get(pk=file.pk)
        assert original.email == "EXEMPLE@EXAMPLE.TEST"
        assert (
            restored.get_model("households", "Member")
            .objects.get(pk=member.pk)
            .first_name
            == "Élodie"
        )
    finally:
        _migrate(latest)


def test_search_upgrade_reuses_extensions_in_another_schema_without_moving_them():
    """Keep shared extensions in place while creating working keys and indexes."""
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        _migrate(BEFORE_SEARCH)
        with connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA "iris_search_test_extensions"')
            cursor.execute(
                'ALTER EXTENSION unaccent SET SCHEMA "iris_search_test_extensions"'
            )
            cursor.execute(
                'ALTER EXTENSION pg_trgm SET SCHEMA "iris_search_test_extensions"'
            )
        _migrate(latest)
        # Use current models and queries so inserts, generated columns and search
        # exercise the installed normalization function after migration commits.
        from modules.households.models import Household
        from modules.households.queries import search

        household = Household.objects.create(
            email="ÉLODIE@EXAMPLE.TEST", phone="+15145550123"
        )
        assert search("elodie@example.test").get().pk == household.pk
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT namespace.nspname FROM pg_extension extension "
                "JOIN pg_namespace namespace ON namespace.oid = extension.extnamespace "
                "WHERE extension.extname IN ('unaccent', 'pg_trgm')"
            )
            assert cursor.fetchall() == [
                ("iris_search_test_extensions",),
                ("iris_search_test_extensions",),
            ]
    finally:
        with connection.cursor() as cursor:
            cursor.execute("ALTER EXTENSION unaccent SET SCHEMA public")
            cursor.execute("ALTER EXTENSION pg_trgm SET SCHEMA public")
        # Recreate the wrapper after restoring namespaces; the previous function
        # deliberately pinned the temporary dictionary namespace.
        _migrate(BEFORE_SEARCH)
        _migrate(latest)
        with connection.cursor() as cursor:
            cursor.execute('DROP SCHEMA IF EXISTS "iris_search_test_extensions"')
