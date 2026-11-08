# AI contribution: 50% or more AI-generated
"""Read household files, search staff records and preview duplicates."""

import re
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.db.models import OuterRef, Q, QuerySet, Subquery, Value
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.households.models import Household, Member
from modules.households.policies import StaffActor, can_manage_walk_ins
from modules.households.search_expressions import SearchKey

DUPLICATE_CANDIDATE_STATUSES = (
    Household.Status.SUBMITTED,
    Household.Status.REVIEW_REQUIRED,
    Household.Status.AWAITING_VISIT,
    Household.Status.APPROVED,
    Household.Status.RENEWAL_NEEDED,
    Household.Status.SUSPENDED,
)


def walk_ins_for_staff(staff_user: AbstractBaseUser) -> QuerySet[Household]:
    households = Household.objects.filter(
        channel=Household.Channel.WALK_IN, anonymized_at__isnull=True
    )
    if not staff_user.is_authenticated or not staff_user.is_active:
        return households.none()
    role = getattr(staff_user, "role", None)
    if role == "admin":
        return households
    if role == "intake_worker":
        return households.filter(created_by_id=staff_user.pk)
    return households.none()


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


def search_for_staff(q: str, actor: StaffActor) -> QuerySet[Household]:
    """Apply ownership before counting, pagination and disclosure audits."""
    if actor is None or not can_manage_walk_ins(actor):
        raise PermissionDenied(
            _("Only active intake workers and admins can manage walk-ins.")
        )
    households = search(q)
    if getattr(actor, "role", None) == "intake_worker":
        households = households.filter(
            Q(channel=Household.Channel.ONLINE) | Q(created_by_id=actor.pk)
        )
    return households


def _matching_ids(households: QuerySet[Household], value: str) -> QuerySet:
    """Combine stored keys without compiling a UNION for every request."""
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

    return households.filter(matches).values("pk")


def search(q: str) -> QuerySet[Household]:
    """Read identifying fields only, with case/accents folded by PostgreSQL.

    Input stays in bound ORM parameters, including LIKE wildcard characters.
    Anonymized files and DOB-containing duplicate keys are never searched.
    API callers use search_for_staff to enforce roles and ownership.
    """
    value = " ".join(q.split())
    households = Household.objects.filter(anonymized_at__isnull=True)
    if not value:
        return households.none()
    matches = _matching_ids(households, value)
    holder = Member.objects.filter(
        household_id=OuterRef("pk"), relation=Member.Relation.HOLDER
    )
    return (
        households.filter(pk__in=matches)
        .annotate(
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
