# AI contribution: 50% or more AI-generated
"""The search migration backfills derived keys and reverses without losing files."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)
BEFORE_SEARCH = [("households", "0003_household_consent")]


def _migrate(target):
    executor = MigrationExecutor(connection)
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def test_existing_households_and_members_survive_search_upgrade_and_reverse():
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
