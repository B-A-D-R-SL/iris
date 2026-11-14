# AI contribution: 50% or more AI-generated
"""Public service for persistent household eligibility decisions."""

import logging
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from modules.accounts.queries import STAFF_ROLES
from modules.audit import services as audit_services
from modules.eligibility.domain.eligibility import decide
from modules.eligibility.models import EligibilityDecision
from modules.households import queries as household_queries
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.eligibility")


class EligibilityEvidenceUnavailableError(ValueError):
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


def _validate_decider(decided_by: object | None) -> AbstractBaseUser | None:
    """Allow automatic decisions or a persisted, active staff actor."""
    if decided_by is not None and (
        not isinstance(decided_by, get_user_model())
        or decided_by._state.adding
        or getattr(decided_by, "pk", None) is None
        or getattr(decided_by, "role", None) not in STAFF_ROLES
        or not getattr(decided_by, "is_active", False)
    ):
        raise PermissionDenied("Only active intake staff may record staff decisions.")
    return decided_by


def _validated_evidence(household_id: UUID) -> tuple[int, list[int]]:
    """Read complete verified evidence through the public household query."""
    reader = getattr(household_queries, "eligibility_inputs", None)
    if not callable(reader):
        raise EligibilityEvidenceUnavailableError(
            "Verified household eligibility evidence is not available."
        )

    snapshot = reader(household_id)
    household = getattr(snapshot, "household", None)

    if household is None or household.pk != household_id:
        raise EligibilityEvidenceUnavailableError("Household evidence is unavailable.")

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
        raise EligibilityEvidenceUnavailableError(
            "Complete confirmed adult income evidence is required."
        )

    return household_size, incomes


def _log_decision_after_commit(
    decision: EligibilityDecision, rule_version: int
) -> None:
    """Log only committed decisions, capturing safe scalar fields now."""
    event_fields = {
        "event": "eligibility_decided",
        "decision_id": decision.pk,
        "household_id": decision.household_id,
        "outcome": "eligible" if decision.eligible else "ineligible",
        "rule_version": rule_version,
    }
    transaction.on_commit(
        lambda: logger.info("eligibility_decided", extra=event_fields),
        robust=True,
    )


@transaction.atomic
def decide_for_household(
    household_id: UUID,
    decided_by: object | None,
) -> EligibilityDecision:
    """Append a decision from verified adult evidence and the active LICO rule."""
    if not isinstance(household_id, UUID):
        raise ValidationError("A valid household UUID is required.")
    decided_by = _validate_decider(decided_by)
    household_size, incomes = _validated_evidence(household_id)

    rule = rule_queries.active("lico_thresholds", at=timezone.now())
    if rule is None:
        raise ValidationError("No active LICO threshold rule is published.")

    threshold_year, thresholds = _validated_thresholds(rule.values)
    result = decide(household_size, incomes, thresholds)

    decision = EligibilityDecision(
        household_id=household_id,
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
    audit_services.record(
        decided_by,
        "decision",
        "household",
        household_id,
        {
            "decision_id": str(decision.pk),
            "outcome": "eligible" if decision.eligible else "ineligible",
            "rule_version": rule.version,
        },
    )
    _log_decision_after_commit(decision, rule.version)
    return decision
