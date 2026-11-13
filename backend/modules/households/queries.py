# AI contribution: 50% or more AI-generated
"""Household files, verified income evidence, staff search and duplicate previews."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import OuterRef, Q, QuerySet, Subquery, Value
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.documents import queries as document_queries
from modules.households.domain.address import normalize_postal_code
from modules.households.domain.names import short_full_name, short_name
from modules.households.domain.notice_name import notice_name_matches
from modules.households.domain.person import is_adult
from modules.households.models import Household, Member
from modules.households.policies import StaffActor, can_manage_walk_ins
from modules.households.search_expressions import SearchKey
from modules.rules import queries as rule_queries

DUPLICATE_CANDIDATE_STATUSES = (
    Household.Status.SUBMITTED,
    Household.Status.REVIEW_REQUIRED,
    Household.Status.AWAITING_VISIT,
    Household.Status.APPROVED,
    Household.Status.RENEWAL_NEEDED,
    Household.Status.SUSPENDED,
)


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


def walk_ins_for_staff(staff_user: AbstractBaseUser) -> QuerySet[Household]:
    households = Household.objects.filter(
        channel=Household.Channel.WALK_IN, anonymized_at__isnull=True
    )
    if not can_manage_walk_ins(staff_user):
        return households.none()
    return households


def walk_in_for_staff(
    household_id: UUID, staff_user: AbstractBaseUser
) -> Household | None:
    return (
        walk_ins_for_staff(staff_user)
        .select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id)
        .first()
    )


def walk_in_notices(
    household_id: UUID, staff_user: AbstractBaseUser
) -> list[document_queries.IncomeNotice] | None:
    """Current notice of each member of a walk-in file; None when the file is unknown.

    Staff resuming the notices screen see what was already recorded (US-18).
    """
    household = walk_in_for_staff(household_id, staff_user)
    if household is None:
        return None
    notices = document_queries.current_notices(m.pk for m in household.members.all())
    return sorted(notices.values(), key=lambda notice: notice.created_at)


def pickup_names(household_id: UUID) -> dict[str, str | None] | None:
    """The names store staff may see at a pickup (US-44, BR-RES-003).

    Only the holder's and the alternate's first name and last initial leave
    this module. A name that is not on file is None. An anonymized or missing
    household gives None.
    """
    household = (
        Household.objects.filter(pk=household_id, anonymized_at__isnull=True)
        .values("alternate_name")
        .first()
    )
    if household is None:
        return None
    holder = (
        Member.objects.filter(
            household_id=household_id, relation=Member.Relation.HOLDER
        )
        .values("first_name", "last_name")
        .first()
    )
    return {
        "holder": short_name(holder["first_name"], holder["last_name"])
        if holder
        else None,
        "alternate": short_full_name(household["alternate_name"]),
    }


def any_visible_for_pickup(household_ids: Iterable[UUID]) -> bool:
    """True when at least one household is still on file for pickup (BR-RES-003)."""
    return Household.objects.filter(
        pk__in=household_ids, anonymized_at__isnull=True
    ).exists()


def household_for_staff(
    household_id: UUID, staff_user: AbstractBaseUser
) -> Household | None:
    """Return a non-anonymized household for the shared staff detail page."""
    if not can_manage_walk_ins(staff_user):
        return None
    return (
        Household.objects.filter(anonymized_at__isnull=True)
        .select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id)
        .first()
    )


def find_possible_duplicates(household: Household) -> QuerySet[Household]:
    """Preview matches; use services.locked_duplicate_check() before writing."""
    if household._state.adding:
        raise ValueError("A saved household is required.")

    person_keys = household.members.exclude(person_key="").values("person_key")
    person_matches = Member.objects.filter(person_key__in=person_keys).values(
        "household_id"
    )
    matches = Q(pk__in=person_matches)
    if household.address_key:
        matches |= Q(address_key=household.address_key)
    return (
        Household.objects.filter(
            matches,
            Q(expires_at__isnull=True) | Q(expires_at__gte=timezone.now()),
            status__in=DUPLICATE_CANDIDATE_STATUSES,
            anonymized_at__isnull=True,
        )
        .exclude(pk=household.pk)
        .order_by("pk")
    )


def approved_household_id(user_id: UUID, *, at: datetime) -> UUID | None:
    """The ID of the household this user holds, if it is approved at ``at``.

    Approved means status ``approved`` and not yet expired. Expiry is checked
    here as well, because the nightly job that moves expired files to
    ``renewal_needed`` may not have run yet. Suspended, expired and every
    other status give None. Only the ID leaves this module.
    """
    return (
        Household.objects.filter(
            holder_id=user_id,
            status=Household.Status.APPROVED,
            expires_at__gt=at,
        )
        .values_list("id", flat=True)
        .first()
    )


def search_for_staff(q: str, actor: StaffActor) -> QuerySet[Household]:
    """Authorize shared staff scope before searching and paginating.

    BR-HH-ACCESS-001 grants intake workers/admins shared household files;
    created_by records provenance, not exclusive ownership. BR-HH-ACCESS-002
    excludes anonymized households before counting or pagination.
    """
    if not can_manage_walk_ins(actor):
        raise PermissionDenied(
            _("Only active intake workers and admins can manage walk-ins.")
        )
    return search(q)


def _matching_households(
    households: QuerySet[Household], value: str
) -> QuerySet[Household]:
    """Apply matches directly to avoid scanning households a second time."""
    needle = SearchKey(Value(value))
    members = Member.objects.all()
    addresses = Q()
    keys = Q()
    for token in value.split():
        part = SearchKey(Value(token))
        members = members.filter(search_name_key__contains=part)
        addresses &= Q(search_address_text__contains=part)
        keys &= Q(search_address_key__contains=part)

    matches = (
        Q(search_email_key__contains=needle)
        | Q(search_number_key__contains=needle)
        | addresses
        | keys
        | Q(pk__in=members.values("household_id"))
    )
    if re.fullmatch(r"[\d\s()+.\-]+", value):
        digits = re.sub(r"\D", "", value)
        if digits:
            matches |= Q(phone__contains=digits)

    return households.filter(matches)


def search(q: str) -> QuerySet[Household]:
    """Read identifying fields only, with case/accents folded by PostgreSQL.

    Input stays in bound ORM parameters, including LIKE wildcard characters.
    Anonymized files and DOB-containing duplicate keys are never searched.
    API callers use search_for_staff to enforce staff permissions.
    """
    value = " ".join(q.split())
    households = Household.objects.filter(anonymized_at__isnull=True)
    if not value:
        return households.none()
    matches = _matching_households(households, value)
    holder = Member.objects.filter(
        household_id=OuterRef("pk"), relation=Member.Relation.HOLDER
    )
    return (
        matches.annotate(
            first_name=Subquery(holder.values("first_name")[:1]),
            last_name=Subquery(holder.values("last_name")[:1]),
        )
        .only(
            "id",
            "member_number",
            "status",
            "channel",
            "created_by_id",
            "anonymized_at",
            "email",
            "phone",
            "street_number",
            "street_name",
            "unit",
            "city",
            "postal_code",
        )
        .order_by("member_number", "pk")
    )
