# AI contribution: 50% or more AI-generated
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.eligibility.tests.fixtures import THRESHOLDS
from modules.households import queries as household_queries
from modules.households.tests.factories import HouseholdFactory
from modules.rules.services import publish


@pytest.fixture
def staff(db):
    return UserFactory(role="intake_worker")


@pytest.fixture
def household(staff):
    return HouseholdFactory(created_by=staff)


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
