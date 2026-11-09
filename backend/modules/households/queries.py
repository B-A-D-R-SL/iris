# AI contribution: 50% or more AI-generated
"""Household lookups and verified income evidence."""

from dataclasses import dataclass
from uuid import UUID
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.documents import queries as document_queries
from modules.households.domain.address import normalize_postal_code
from modules.households.domain.notice_name import notice_name_matches
from modules.households.domain.person import is_adult
from modules.households.models import Household, Member
from modules.rules import queries as rule_queries


class HouseholdEvidenceUnavailable(ValueError):
    def __init__(self, reasons: set[str]) -> None:
        self.reasons = tuple(sorted(reasons))
        super().__init__(", ".join(self.reasons))


@dataclass(frozen=True)
class EligibilityInputs:
    household: Household
    household_size: int
    adult_count: int
    adult_incomes_cents: list[int]


def _accepted_tax_years() -> list[int]:
    rule = rule_queries.active("auto_approval")
    years = rule.values.get("accepted_tax_years") if rule else None
    if (
        not isinstance(years, list)
        or not years
        or any(type(y) is not int for y in years)
    ):
        raise ValidationError(_("Accepted tax years are not configured."))
    return years


def _notice_reasons(
    member: Member,
    notice: document_queries.IncomeNotice,
    household: Household,
    years: list[int],
) -> set[str]:
    if notice.status == "did_not_file":
        return {"DID_NOT_FILE"}
    reasons = set()
    if notice.tax_year not in years:
        reasons.add("TAX_YEAR_NOT_ACCEPTED")
    if not notice.seen_in_person:
        reasons.add("NOTICE_NOT_SEEN")
    if not notice_name_matches(
        member.first_name, member.last_name, notice.name_on_notice
    ):
        reasons.add("NAME_MISMATCH")
    if normalize_postal_code(notice.postal_code_on_notice) != household.postal_code:
        reasons.add("ADDRESS_MISMATCH")
    return reasons


@transaction.atomic
def eligibility_inputs(household_id: UUID) -> EligibilityInputs:
    # Eligibility and staff edits share the household lock for a stable snapshot.
    household = Household.objects.select_for_update().get(
        pk=household_id, anonymized_at__isnull=True
    )
    members = list(household.members.order_by("pk"))
    today = timezone.localdate(timezone=ZoneInfo("America/Montreal"))
    adults = [m for m in members if is_adult(m.date_of_birth, today)]
    if not any(m.relation == Member.Relation.HOLDER for m in adults):
        raise ValidationError(_("An adult holder is required."))
    notices = document_queries.current_notices(m.pk for m in adults)
    if len(notices) != len(adults):
        raise ValidationError(
            _("Record a notice or non-filing reason for every adult.")
        )
    years = _accepted_tax_years()
    reasons: set[str] = set()
    for member in adults:
        reasons.update(_notice_reasons(member, notices[member.pk], household, years))
    if reasons:
        # A non-filer or unverified notice must never become an assumed zero income.
        raise HouseholdEvidenceUnavailable(reasons)
    incomes = []
    for member in adults:
        amount = notices[member.pk].total_income_cents
        if type(amount) is not int or amount < 0:
            raise HouseholdEvidenceUnavailable({"INCOME_NOT_CONFIRMED"})
        incomes.append(amount)
    return EligibilityInputs(household, len(members), len(adults), incomes)


def walk_in_for_staff(household_id: UUID) -> Household | None:
    return (
        Household.objects.select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id, channel=Household.Channel.WALK_IN)
        .first()
    )
