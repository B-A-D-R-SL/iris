# AI contribution: 50% or more AI-generated
"""Write operations for versioned business-rule settings."""

import logging
from datetime import datetime
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from modules.audit.services import record
from modules.rules.domain.schemas import (
    RuleValidationError,
    validate_rule_values,
)
from modules.rules.models import RuleSetVersion

logger = logging.getLogger("iris.rules")


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
        rule = _create_version(normalized_rule_type, values, user, effective_at)
        record(
            user,
            "rule_published",
            "rule_set_version",
            rule.pk,
            {"rule_type": rule.rule_type, "version": rule.version},
        )
        transaction.on_commit(
            lambda: logger.info("rule_published", extra={"event": "rule_published"})
        )
        return rule


def _create_version(
    rule_type: str,
    values: dict[str, Any],
    user: AbstractBaseUser,
    effective_at: datetime,
) -> RuleSetVersion:
    """Create the next version while holding the latest row lock."""
    latest = (
        RuleSetVersion.objects.select_for_update()
        .filter(rule_type=rule_type)
        .order_by("-version")
        .first()
    )
    return RuleSetVersion.objects.create(  # type: ignore[misc]
        rule_type=rule_type,
        version=1 if latest is None else latest.version + 1,
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

    try:
        validate_rule_values(rule_type, values)
    except RuleValidationError as exc:
        raise ValidationError(exc.errors) from exc


def _validate_effective_from(effective_from: datetime) -> None:
    if timezone.is_naive(effective_from):
        raise ValidationError("effective_from must be timezone-aware.")
