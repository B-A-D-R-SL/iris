# AI contribution: 50% or more AI-generated
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.utils import timezone

from modules.eligibility.tests.fixtures import THRESHOLDS
from modules.households import queries as household_queries
from modules.rules.services import publish


@pytest.fixture
def staff(django_user_model):
    return django_user_model.objects.create_user(
        "eligibility-staff@example.test",
        role="intake_worker",
    )


@pytest.fixture
def household(staff):
    household_model = apps.get_model("households", "Household")
    walk_in_channel = next(
        value
        for value, _ in household_model._meta.get_field("channel").choices
        if value in {"walk-in", "walk_in"}
    )
    return household_model.objects.create(
        channel=walk_in_channel,
        status="draft",
        street_number="100",
        street_name="Rue Exemple",
        city="Montréal",
        postal_code="H2X 1Y4",
        address_key="100-rue-exemple-h2x1y4",
        phone="+15145550100",
        created_by=staff,
    )


@pytest.fixture
def lico(staff):
    return publish(
        "lico_thresholds",
        {
            "year": 2025,
            "source_url": "https://www.statcan.gc.ca/",
            "retrieved_on": "2026-10-01",
            "thresholds": THRESHOLDS.copy(),
        },
        staff,
        effective_from=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def confirmed_inputs(household, monkeypatch):
    snapshot = SimpleNamespace(
        household=household,
        household_size=3,
        adult_count=2,
        adult_incomes_cents=[12_345, 20_000],
    )
    monkeypatch.setattr(
        household_queries,
        "eligibility_inputs",
        lambda household_id: snapshot if household_id == household.pk else None,
        raising=False,
    )
    return snapshot
