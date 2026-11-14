# AI contribution: 50% or more AI-generated
"""Approve a walk-in file: the decision staff ask for after submission (US-18)."""

from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.eligibility import services as eligibility_services
from modules.households import _approval, queries
from modules.households.domain.expiry import InvalidApprovedMonths
from modules.households.models import Household
from modules.households.policies import require_walk_in_staff


@transaction.atomic
def approve_walk_in(household: Household, staff: AbstractBaseUser) -> Household:
    require_walk_in_staff(staff)
    if getattr(staff, "pk", None) is None or getattr(
        getattr(staff, "_state", None), "adding", True
    ):
        raise PermissionDenied(
            _("Only active intake workers and admins can manage walk-ins.")
        )
    # Draft editing and notice entry take this same lock before changing evidence.
    locked = Household.objects.select_for_update().get(
        pk=household.pk,
        channel=Household.Channel.WALK_IN,
        anonymized_at__isnull=True,
    )
    if locked.status == Household.Status.DRAFT:
        # BR-DUP-002: approval follows submission, which runs the duplicate check.
        raise ValidationError(_("Submit the file before approving it."))
    if locked.status == Household.Status.REVIEW_REQUIRED:
        # Approving again cannot change a review outcome; it would only repeat rows.
        raise ValidationError(_("This file is already waiting for review."))
    if locked.status != Household.Status.SUBMITTED:
        raise ValidationError(
            _("This household file cannot be approved in its current status.")
        )
    locked.full_clean()
    _approval.apply_outcome(locked, staff)
    invited = _approval.record_outcome(locked, staff)
    # Not saved: tells the caller whether a set-password email was queued.
    locked.invitation_not_sent = not invited  # type: ignore[attr-defined]
    return locked


@dataclass(frozen=True)
class DecisionSummary:
    """The facts and next step shown before the decision (US-18, Figma W6.2b)."""

    household_size: int
    adult_count: int
    total_income_cents: int | None
    threshold_cents: int | None
    ready_for_decision: bool
    will_go_to_review: bool
    # Null while the file goes to review: eligibility is not decided yet.
    eligible: bool | None
    # Set only when approval would approve the file: how long it lasts and until when.
    approved_months: int | None
    valid_until: datetime | None


def _validity_if_approved_now() -> tuple[int | None, datetime | None]:
    """The months and end date approval would save; nothing when the rule is broken.

    A broken rule is not hidden: approving still refuses with its own message.
    """
    try:
        return _approval.validity(timezone.now())
    except (InvalidApprovedMonths, OverflowError, ValueError):
        return None, None


def decision_summary(household: Household, staff: AbstractBaseUser) -> DecisionSummary:
    """Read-only: what approval would use and where it would lead."""
    require_walk_in_staff(staff)
    evidence = queries.decision_evidence(household)
    # After submission notices are locked: a missing one (a member who turned 18)
    # cannot be fixed, so approving sends the file to review.
    unfixable = not evidence.complete and household.status != Household.Status.DRAFT
    ready = evidence.complete or unfixable
    review = (
        bool(evidence.review_reasons)
        or unfixable
        or household.status == Household.Status.REVIEW_REQUIRED
    )
    income = threshold = eligible = None
    if evidence.complete and not evidence.review_reasons:
        try:
            preview = eligibility_services.preview_for_household(household.pk)
        except queries.HouseholdEvidenceUnavailable:
            review = True  # an income that cannot be confirmed goes to review
        else:
            income, threshold = preview.household_income_cents, preview.threshold_cents
            eligible = preview.eligible
    approved_months = valid_until = None
    if not review and eligible:
        approved_months, valid_until = _validity_if_approved_now()
    return DecisionSummary(
        household_size=evidence.household_size,
        adult_count=evidence.adult_count,
        total_income_cents=income,
        threshold_cents=threshold,
        ready_for_decision=ready,
        will_go_to_review=ready and review,
        eligible=None if review else eligible,
        approved_months=approved_months,
        valid_until=valid_until,
    )
