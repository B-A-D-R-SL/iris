# AI contribution: 50% or more AI-generated
"""Approval steps used inside the household service's transaction."""

from typing import Any
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.accounts import services as account_services
from modules.audit import services as audit_services
from modules.eligibility import services as eligibility_services
from modules.households.domain.expiry import InvalidApprovedMonths, approved_expiry
from modules.households.models import Household, Member
from modules.households.queries import HouseholdEvidenceUnavailable
from modules.notifications import services as notification_services
from modules.rules import queries as rule_queries


def check_complete(household: Household) -> None:
    if not household.members.filter(relation=Member.Relation.HOLDER).exists():
        raise ValidationError(_("An adult holder is required."))
    if not all(
        (
            household.street_number,
            household.street_name,
            household.city,
            household.postal_code,
            household.phone,
        )
    ):
        raise ValidationError(_("Complete the household address and telephone number."))
    if not household.consent_data_processing_at or not household.consent_text_version:
        raise ValidationError(_("Data-processing consent is required."))


def apply_outcome(household: Household, staff: Any) -> None:
    reasons = {household.status_reason} if household.status_reason else set()
    if household.status == Household.Status.REVIEW_REQUIRED and not reasons:
        reasons.add("REVIEW_REQUIRED")
    if not household.identity_checked_in_person:
        reasons.add("IDENTITY_NOT_VERIFIED")
    decision = None
    try:
        decision = eligibility_services.decide_for_household(household.pk, staff)
    except HouseholdEvidenceUnavailable as exc:
        reasons.update(exc.reasons)
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
        rule = rule_queries.active("file_validity", at=household.approved_at)
        months = rule.values.get("approved_months") if rule else None
        try:
            household.expires_at = approved_expiry(
                timezone.localtime(household.approved_at, ZoneInfo("America/Montreal")),
                months,
            )
        except (InvalidApprovedMonths, OverflowError, ValueError) as exc:
            raise ValidationError(
                _("File validity is not configured correctly.")
            ) from exc


def record_outcome(household: Household, staff: Any) -> None:
    household.full_clean()
    household.save()
    audit_services.record(
        staff, "decision", "household", household.pk, {"outcome": household.status}
    )
    if household.status != Household.Status.APPROVED or not household.email:
        return
    holder = household.members.get(relation=Member.Relation.HOLDER)
    token = account_services.create_invitation(
        email=household.email,
        first_name=holder.first_name,
        last_name=holder.last_name,
        role="beneficiary",
        invited_by=staff,
    )
    notification_services.queue_set_password_email(
        email=household.email,
        token=token,
        language=household.preferred_language,
    )
