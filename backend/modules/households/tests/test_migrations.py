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
