# AI contribution: 50% or more AI-generated
"""Generated valid decision snapshots for tests; callers supply a published rule."""

import factory

from modules.eligibility.models import EligibilityDecision
from modules.households.tests.factories import HouseholdFactory


class EligibilityDecisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EligibilityDecision

    household = factory.SubFactory(HouseholdFactory)
    household_size = 1
    adult_incomes_cents = factory.LazyFunction(lambda: [50])
    household_income_cents = 50
    threshold_cents = 100
    threshold_year = 2025
    eligible = True
    decided_by_type = EligibilityDecision.DecidedByType.AUTOMATIC
    decided_by = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        decision = model_class(*args, **kwargs)
        decision.full_clean()
        decision.save(force_insert=True)
        return decision
