"""Persistent, immutable versions of Iris business-rule settings."""

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImmutableRuleSetVersionQuerySet(models.QuerySet["RuleSetVersion"]):
    """Disallow bulk mutations that would rewrite published rule history."""

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Published rule versions cannot be deleted.")

    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Published rule versions cannot be updated.")


class RuleSetVersion(models.Model):
    """One published version of the values for a business-rule type.

    A version is an audit record, not a mutable draft. Publishing creates a new
    row so decisions can always be resolved against the rules effective at the
    time they were made.
    """

    rule_type = models.CharField(max_length=100)
    version = models.PositiveIntegerField()
    values = models.JSONField()
    effective_from = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="published_rule_set_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableRuleSetVersionQuerySet.as_manager()

    class Meta:
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.UniqueConstraint(
                fields=["rule_type", "version"],
                name="rules_unique_type_version",
            )
        ]
        indexes = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.Index(
                fields=["rule_type", "effective_from", "version"],
                name="rules_active_lookup_idx",
            )
        ]
        ordering = [  # noqa: RUF012 - Django reads declarative model metadata.
            "rule_type",
            "effective_from",
            "version",
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Allow creation only; published rows must remain historical facts."""
        if not self._state.adding:
            raise ValidationError("Published rule versions cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        """Keep rule history available for historical decision lookups."""
        raise ValidationError("Published rule versions cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.rule_type} v{self.version}"
