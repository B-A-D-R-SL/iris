# AI contribution: 50% or more AI-generated
from typing import Any
from uuid import uuid4

import pytest
from django.apps import apps
from django.utils import timezone

from modules.households.tests.factories import HouseholdFactory
from modules.rules.services import publish


@pytest.fixture
def actor(db, django_user_model):
    return django_user_model.objects.create_user(
        "generated@example.test", role="intake_worker", first_name="Example"
    )


@pytest.fixture
def event_inputs(actor) -> dict[str, Any]:
    return {
        "actor": actor,
        "action": "view",
        "target_type": "household",
        "target_id": uuid4(),
        "metadata": {},
    }


@pytest.fixture
def suspension_rule(actor):
    """Publish the reason limit required by suspension audit events."""
    return publish("household_suspension", {"reason_max_length": 500}, actor)


@pytest.fixture
def eligibility_inputs(event_inputs):
    event_inputs.update(
        action="decision",
        metadata={
            "decision_id": str(uuid4()),
            "outcome": "eligible",
            "rule_version": 2,
        },
    )
    return event_inputs


@pytest.fixture
def automatic_decision(actor):
    household = HouseholdFactory(created_by=actor)
    rule = publish(
        "lico_thresholds",
        {
            "year": 2025,
            "source_url": "https://www.statcan.gc.ca/",
            "retrieved_on": timezone.localdate().isoformat(),
            "thresholds": {str(size): size * 100 for size in range(1, 8)},
        },
        actor,
    )
    model = apps.get_model("eligibility", "EligibilityDecision")
    return model.objects.create(
        household=household,
        household_size=1,
        adult_incomes_cents=[50],
        household_income_cents=50,
        threshold_cents=100,
        threshold_year=2025,
        ruleset_version=rule,
        eligible=True,
        decided_by_type="automatic",
        decided_by=None,
    )


@pytest.fixture
def system_inputs(event_inputs, automatic_decision):
    return {
        **event_inputs,
        "actor": None,
        "action": "decision",
        "target_id": automatic_decision.household_id,
        "metadata": {
            "decision_id": str(automatic_decision.pk),
            "outcome": "eligible",
            "rule_version": automatic_decision.ruleset_version.version,
        },
    }
