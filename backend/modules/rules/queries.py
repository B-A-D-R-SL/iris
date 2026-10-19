"""Read-only access to versioned business-rule settings."""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from modules.rules.models import RuleSetVersion


def active(rule_type: str, at: datetime | None = None) -> RuleSetVersion | None:
    """Return the rule version in effect for ``rule_type`` at ``at``.

    A later version number does not necessarily have a later effective date.
    Ordering by effective time first therefore keeps historical lookups correct
    when a correction is published with a backdated effective date.
    """
    if not isinstance(rule_type, str) or not (
        normalized_rule_type := rule_type.strip()
    ):
        raise ValidationError("rule_type must be a non-empty string.")

    effective_at = timezone.now() if at is None else at
    if timezone.is_naive(effective_at):
        raise ValidationError("at must be timezone-aware.")

    return (
        RuleSetVersion.objects.filter(
            rule_type=normalized_rule_type,
            effective_from__lte=effective_at,
        )
        .order_by("-effective_from", "-version")
        .first()
    )
