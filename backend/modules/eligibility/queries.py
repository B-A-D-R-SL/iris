# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for eligibility."""

from uuid import UUID

from modules.eligibility.models import EligibilityDecision


def automatic_decision_matches_audit(
    decision_id: str, household_id: str, outcome: str, rule_version: int
) -> bool:
    """Verify system attribution and references against an immutable decision."""
    try:
        household_uuid = UUID(household_id)
    except ValueError:
        return False
    return EligibilityDecision.objects.filter(
        pk=decision_id,
        household_id=household_uuid,
        decided_by_type=EligibilityDecision.DecidedByType.AUTOMATIC,
        decided_by_id__isnull=True,
        eligible=outcome == "eligible",
        ruleset_version__version=rule_version,
    ).exists()
