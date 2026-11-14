# AI contribution: 50% or more AI-generated
"""Approval steps used inside the household service's transaction."""

import logging
from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.accounts import services as account_services
from modules.accounts.roles import UserRole
from modules.audit import services as audit_services
from modules.eligibility import services as eligibility_services
from modules.households.domain.expiry import InvalidApprovedMonths, approved_expiry
from modules.households.models import Household, Member
from modules.households import queries
from modules.households.queries import HouseholdEvidenceUnavailable
from modules.notifications import services as notification_services
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.households")


def validity(approved_at: datetime) -> tuple[int, datetime]:
    """How many months a file approved at this moment lasts, and when it ends.

    Both the approval and the decision summary use this, so the screen shows the
    same date the approval saves. Raises InvalidApprovedMonths, OverflowError or
    ValueError when the file_validity rule is missing or broken.
    """
    rule = rule_queries.active("file_validity", at=approved_at)
    months = rule.values.get("approved_months") if rule else None
    until = approved_expiry(
        timezone.localtime(approved_at, ZoneInfo("America/Montreal")), months
    )
    return cast(int, months), until


def apply_outcome(household: Household, staff: Any) -> None:
    reasons = {household.status_reason} if household.status_reason else set()
    decision = None
    if queries.decision_evidence(household).complete:
        try:
            decision = eligibility_services.decide_for_household(household.pk, staff)
        except HouseholdEvidenceUnavailable as exc:
            reasons.update(exc.reasons)
    else:
        # Notices are locked after submission, so a member who turned 18 since then
        # has none: the file goes to review instead of staying stuck.
        reasons.add("NOTICE_MISSING")
    household.approved_at = household.expires_at = None
    if reasons:
        household.status = Household.Status.REVIEW_REQUIRED
        household.status_reason = ", ".join(sorted(reasons))
    elif decision is not None and not decision.eligible:
        household.status = Household.Status.REJECTED
        household.status_reason = "INCOME_ABOVE_LICO"
    else:
        household.status = Household.Status.APPROVED
        household.status_reason = ""
        household.approved_at = timezone.now()
        try:
            household.expires_at = validity(household.approved_at)[1]
        except (InvalidApprovedMonths, OverflowError, ValueError) as exc:
            raise ValidationError(
                _("File validity is not configured correctly.")
            ) from exc


def _log_outcome(household: Household) -> None:
    """Log the outcome once the transaction commits; codes only, no personal data."""
    outcome, reason, household_id = (
        household.status,
        household.status_reason,
        str(household.pk),
    )
    transaction.on_commit(
        lambda: logger.info(
            "walk_in_decision",
            extra={
                "event": "walk_in_decision",
                "household_id": household_id,
                "outcome": outcome,
                "reason_codes": reason,
            },
        )
    )


def _log_invitation_skipped(household: Household) -> None:
    household_id = str(household.pk)
    transaction.on_commit(
        lambda: logger.info(
            "walk_in_invitation_skipped",
            extra={
                "event": "walk_in_invitation_skipped",
                "household_id": household_id,
                "reason": "email_already_registered",
            },
        )
    )


def record_outcome(household: Household, staff: Any) -> bool:
    """Save the outcome; return whether a set-password invitation was queued.

    An email that already has an account cannot be invited. The approval still
    stands (the household is served at the counter), staff are told, and the
    invitation is skipped.
    """
    household.full_clean()
    household.save()
    audit_services.record(
        staff, "decision", "household", household.pk, {"outcome": household.status}
    )
    _log_outcome(household)
    if household.status != Household.Status.APPROVED or not household.email:
        return True
    holder = household.members.get(relation=Member.Relation.HOLDER)
    try:
        token = account_services.create_invitation(
            email=household.email,
            first_name=holder.first_name,
            last_name=holder.last_name,
            role=UserRole.BENEFICIARY,
            invited_by=staff,
        )
    except ValidationError as exc:
        if exc.code != "email_already_registered":
            raise
        _log_invitation_skipped(household)
        return False
    notification_services.queue_set_password_email(
        email=household.email,
        token=token,
        language=household.preferred_language,
    )
    return True
