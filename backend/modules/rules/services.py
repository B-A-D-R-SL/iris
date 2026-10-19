"""Write operations for versioned business-rule settings."""

from datetime import datetime
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from modules.rules.domain.schemas import validate_rule_values
from modules.rules.models import RuleSetVersion


def publish(
    rule_type: str,
    values: dict[str, Any],
    user: AbstractBaseUser,
    *,
    effective_from: datetime | None = None,
) -> RuleSetVersion:
    """Publish the next immutable version for ``rule_type``.

    ``effective_from`` is optional so ordinary publications take effect now,
    while corrections can be published for an earlier or future instant. The
    version number remains monotonically increasing even when effective dates
    are not, because the resolver uses effective dates rather than version
    number to answer historical questions.
    """
    normalized_rule_type = _validate_rule_type(rule_type)
    _validate_values(normalized_rule_type, values)
    effective_at = timezone.now() if effective_from is None else effective_from
    _validate_effective_from(effective_at)

    with transaction.atomic():
        latest_version = (
            RuleSetVersion.objects.select_for_update()
            .filter(rule_type=normalized_rule_type)
            .order_by("-version")
            .first()
        )
        next_version = 1 if latest_version is None else latest_version.version + 1
        return RuleSetVersion.objects.create(  # type: ignore[misc]
            rule_type=normalized_rule_type,
            version=next_version,
            values=values,
            effective_from=effective_at,
            created_by=user,
        )


def _validate_rule_type(rule_type: str) -> str:
    if not isinstance(rule_type, str) or not (
        normalized_rule_type := rule_type.strip()
    ):
        raise ValidationError("rule_type must be a non-empty string.")
    return normalized_rule_type


def _validate_values(rule_type: str, values: dict[str, Any]) -> None:
    if not isinstance(values, dict):
        raise ValidationError("Rule values must be a JSON object.")
    validate_rule_values(rule_type, values)


def _validate_effective_from(effective_from: datetime) -> None:
    if timezone.is_naive(effective_from):
        raise ValidationError("effective_from must be timezone-aware.")
