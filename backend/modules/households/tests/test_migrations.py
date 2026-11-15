# AI contribution: 50% or more AI-generated
"""Upgrade of a database seeded by SET-18 (#617) to the US-17 model (#461)."""

import uuid

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from modules.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db(transaction=True)

SET18 = [("households", "0001_initial")]


def _migrate(target):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def _latest():
    executor = MigrationExecutor(connection)
    return executor.loader.graph.leaf_nodes("households")


@pytest.fixture(autouse=True)
def _restore_schema():
    try:
        yield
    finally:
        # Rolling households back also un-applies dependent notice migrations.
        executor = MigrationExecutor(connection)
        _migrate(executor.loader.graph.leaf_nodes())


def test_seeded_rows_survive_the_upgrade():
    worker = UserFactory(role="intake_worker")
    old_apps = _migrate(SET18)
    old_household = old_apps.get_model("households", "Household")
    seeded = old_household.objects.create(
        id=uuid.uuid4(),
        channel="walk-in",
        status="approved",
        street_number="12",
        street_name="rue Exemple",
        unit=None,
        city="Montréal",
        postal_code="H0H 0H0",
        address_key="12|rue exemple||montreal|h0h 0h0",
        phone="+15145550100",
        created_by_id=worker.pk,
    )

    new_apps = _migrate(_latest())
    household = new_apps.get_model("households", "Household").objects.get(pk=seeded.pk)
    assert household.channel == "walk_in"
    assert household.unit == ""
    assert household.status == "approved"
    assert household.preferred_language == "fr"
    assert household.identity_checked_in_person is False
    assert household.consent_data_processing_at is None
    assert household.consent_text_version == ""


def test_upgrade_can_be_reversed_to_the_set18_table():
    worker = UserFactory(role="intake_worker")
    new_apps = _migrate(_latest())
    created = new_apps.get_model("households", "Household").objects.create(
        channel="walk_in",
        status="draft",
        street_number="5",
        street_name="rue Saint-Denis",
        unit="",
        city="Montréal",
        postal_code="H2X 1Y4",
        phone="+15145550101",
        created_by_id=worker.pk,
    )

    old_apps = _migrate(SET18)
    household = old_apps.get_model("households", "Household").objects.get(pk=created.pk)
    assert household.channel == "walk-in"
    assert household.unit is None
    _migrate(_latest())


def test_duplicate_keys_are_backfilled_without_changing_source_data():
    old_apps = _migrate([("households", "0003_household_consent")])
    old_households = old_apps.get_model("households", "Household")
    household = old_households.objects.create(
        street_number="12",
        street_name="rue Émile",
        unit="4",
        city="Montréal",
        postal_code="h2x 1y4",
        phone="+15145550100",
        status="approved",
        address_key="12|rue émile|4|montreal|h2x 1y4",
    )
    old_member = old_apps.get_model("households", "Member").objects.create(
        household=household,
        first_name="Émilie",
        last_name=" Exemple ",
        date_of_birth="1990-01-01",
        relation="holder",
        person_key="",
    )
    try:
        new_apps = _migrate(_latest())
        restored = new_apps.get_model("households", "Household").objects.get(
            pk=household.pk
        )
        member = new_apps.get_model("households", "Member").objects.get(
            pk=old_member.pk
        )
        assert restored.address_key == "12|R EMILE|4|H2X1Y4"
        assert restored.street_name == "rue Émile"
        assert restored.postal_code == "h2x 1y4"
        assert restored.status == "approved"
        assert member.person_key == "EXEMPLE|EMILIE|1990-01-01"
        assert member.last_name == " Exemple "
        # Rollback keeps the updated keys.
        reversed_apps = _migrate([("households", "0003_household_consent")])
        assert (
            reversed_apps.get_model("households", "Household")
            .objects.get(pk=household.pk)
            .address_key
            == "12|R EMILE|4|H2X1Y4"
        )
    finally:
        _migrate(_latest())


def test_duplicate_backfill_leaves_incomplete_or_anonymized_keys_empty():
    from django.utils import timezone

    old_apps = _migrate([("households", "0003_household_consent")])
    model = old_apps.get_model("households", "Household")
    incomplete = model.objects.create(phone="+15145550100", address_key="stale")
    anonymized = model.objects.create(
        street_number="12",
        street_name="rue Exemple",
        city="Montréal",
        postal_code="H2X 1Y4",
        phone="+15145550100",
        address_key="stale",
        anonymized_at=timezone.now(),
    )
    member = old_apps.get_model("households", "Member").objects.create(
        household=anonymized,
        first_name="Example",
        last_name="Person",
        date_of_birth="1990-01-01",
        relation="holder",
        person_key="stale",
    )
    try:
        new_apps = _migrate(_latest())
        households = new_apps.get_model("households", "Household")
        assert households.objects.get(pk=incomplete.pk).address_key == ""
        assert households.objects.get(pk=anonymized.pk).address_key == ""
        assert (
            new_apps.get_model("households", "Member")
            .objects.get(pk=member.pk)
            .person_key
            == ""
        )
    finally:
        _migrate(_latest())
