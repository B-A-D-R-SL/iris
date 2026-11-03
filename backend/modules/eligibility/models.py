# AI contribution: 50% or more AI-generated
"""Immutable eligibility decision records."""

import uuid
from typing import Any

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ImmutableDecisionQuerySet(models.QuerySet["EligibilityDecision"]):
    """Prevent ordinary ORM operations from rewriting decision history."""

    def update(self, **kwargs: Any) -> int:
        raise ValidationError("Eligibility decisions cannot be updated.")

    def delete(self) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eligibility decisions cannot be deleted.")


class EligibilityDecision(models.Model):
    """Historical snapshot of one household eligibility calculation."""

    class DecidedByType(models.TextChoices):
        AUTOMATIC = "automatic", "Automatic"
        STAFF = "staff", "Staff"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.PROTECT,
        related_name="eligibility_decisions",
    )
    household_size = models.PositiveSmallIntegerField()
    adult_incomes_cents = ArrayField(models.BigIntegerField(), default=list)
    household_income_cents = models.BigIntegerField()
    threshold_cents = models.BigIntegerField()
    threshold_year = models.PositiveSmallIntegerField()
    ruleset_version = models.ForeignKey(
        "rules.RuleSetVersion",
        on_delete=models.PROTECT,
        related_name="eligibility_decisions",
    )
    eligible = models.BooleanField()
    decided_by_type = models.CharField(
        max_length=9,
        choices=DecidedByType.choices,
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eligibility_decisions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ImmutableDecisionQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]  # noqa: RUF012 - Django metadata.
        constraints = [  # noqa: RUF012 - Django metadata.
            models.CheckConstraint(
                condition=Q(household_size__gte=1),
                name="eligibility_household_size_positive",
            ),
            models.CheckConstraint(
                condition=Q(household_income_cents__gte=0),
                name="eligibility_total_income_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(threshold_cents__gt=0),
                name="eligibility_threshold_positive",
            ),
            models.CheckConstraint(
                condition=Q(decided_by_type__in=["automatic", "staff"]),
                name="eligibility_decider_type_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(decided_by_type="automatic", decided_by__isnull=True)
                    | Q(decided_by_type="staff", decided_by__isnull=False)
                ),
                name="eligibility_decider_consistent",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        incomes = self.adult_incomes_cents

        if (
            not isinstance(incomes, list)
            or not incomes
            or any(type(value) is not int or value < 0 for value in incomes)
        ):
            raise ValidationError(
                {"adult_incomes_cents": "Provide nonnegative integer adult incomes."}
            )

        if self.household_size < len(incomes):
            raise ValidationError(
                {"household_size": "Household size cannot be smaller than adult count."}
            )

        if sum(incomes) != self.household_income_cents:
            raise ValidationError(
                {"household_income_cents": "Total must equal the sum of adult incomes."}
            )

        if self.eligible != (self.household_income_cents <= self.threshold_cents):
            raise ValidationError(
                {"eligible": "Result must match the eligibility calculation."}
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Eligibility decisions cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Eligibility decisions cannot be deleted.")
