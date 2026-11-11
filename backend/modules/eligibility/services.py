# AI contribution: 50% or more AI-generated
"""Public service for persistent household eligibility decisions."""

from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from modules.accounts.queries import STAFF_ROLES
from modules.eligibility.domain.eligibility import decide
from modules.eligibility.models import EligibilityDecision
from modules.households import queries as household_queries
from modules.rules import queries as rule_queries


class EligibilityEvidenceUnavailable(ValueError):
    """Required verified household income evidence is unavailable."""


def _validated_thresholds(values: object) -> tuple[int, dict[int, int]]:
    """Extract a complete, validated LICO snapshot from a published rule."""
    if not isinstance(values, dict):
        raise ValidationError("Invalid LICO rule configuration.")

    year = values.get("year")
    raw = values.get("thresholds")

    if type(year) is not int or not 2000 <= year <= 9999:
        raise ValidationError("Invalid LICO reference year.")
    if not isinstance(raw, dict):
        raise ValidationError("Invalid LICO thresholds.")

    expected = {str(size) for size in range(1, 8)}
    if set(raw) != expected:
        raise ValidationError("LICO configuration must contain sizes 1 through 7.")

    if any(type(value) is not int or value <= 0 for value in raw.values()):
        raise ValidationError("LICO thresholds must be positive integer cents.")

    return year, {size: raw[str(size)] for size in range(1, 8)}


@transaction.atomic
def decide_for_household(
    household_id: UUID,
    decided_by: object | None,
) -> EligibilityDecision:
    """Record a new decision from verified household evidence and active rules.

    The household query contract must return an object containing:
      household: persisted Household instance
      household_size: full member count including children
      adult_count: number of household members aged 18 or more
      adult_incomes_cents: list of confirmed line-199 amounts, one per adult

    Adult selection, accepted notices, and missing-evidence rejection are
    the responsibility of the public households query interface.
    """
    if not isinstance(household_id, UUID):
        raise ValidationError("A valid household UUID is required.")

    if decided_by is not None and (
        not isinstance(decided_by, get_user_model())
        or getattr(decided_by, "pk", None) is None
        or getattr(decided_by, "role", None) not in STAFF_ROLES
        or not getattr(decided_by, "is_active", False)
    ):
        raise PermissionDenied("Only active intake staff may record staff decisions.")

    reader = getattr(household_queries, "eligibility_inputs", None)
    if not callable(reader):
        raise EligibilityEvidenceUnavailable(
            "Verified household eligibility evidence is not available."
        )

    snapshot = reader(household_id)
    household = getattr(snapshot, "household", None)

    if household is None or household.pk != household_id:
        raise EligibilityEvidenceUnavailable("Household evidence is unavailable.")

    household_size = getattr(snapshot, "household_size", None)
    adult_count = getattr(snapshot, "adult_count", None)
    incomes = getattr(snapshot, "adult_incomes_cents", None)

    if (
        type(household_size) is not int
        or household_size < 1
        or type(adult_count) is not int
        or adult_count < 1
        or adult_count > household_size
        or not isinstance(incomes, list)
        or len(incomes) != adult_count
        or any(type(value) is not int or value < 0 for value in incomes)
    ):
        raise EligibilityEvidenceUnavailable(
            "Complete confirmed adult income evidence is required."
        )

    rule = rule_queries.active("lico_thresholds", at=timezone.now())
    if rule is None:
        raise ValidationError("No active LICO threshold rule is published.")

    threshold_year, thresholds = _validated_thresholds(rule.values)
    result = decide(household_size, incomes, thresholds)

    decision = EligibilityDecision(
        household=household,
        household_size=household_size,
        adult_incomes_cents=list(incomes),
        household_income_cents=result.household_income_cents,
        threshold_cents=result.threshold_cents,
        threshold_year=threshold_year,
        ruleset_version=rule,
        eligible=result.eligible,
        decided_by_type=(
            EligibilityDecision.DecidedByType.STAFF
            if decided_by is not None
            else EligibilityDecision.DecidedByType.AUTOMATIC
        ),
        decided_by_id=getattr(decided_by, "pk", None),
    )
    decision.full_clean()
    decision.save(force_insert=True)
    return decision
