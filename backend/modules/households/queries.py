# AI contribution: 50% or more AI-generated
"""Read-only public interfaces for household files and staff search."""

import re
from datetime import datetime
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db.models import OuterRef, Q, QuerySet, Subquery, Value
from django.utils.translation import gettext_lazy as _

from modules.households.models import Household, Member
from modules.households.policies import StaffActor, can_manage_walk_ins
from modules.households.search_expressions import SearchKey


def walk_in_for_staff(household_id: UUID) -> Household | None:
    """Read a shared walk-in file, excluding anonymized records."""
    return (
        Household.objects.select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(
            pk=household_id,
            channel=Household.Channel.WALK_IN,
            anonymized_at__isnull=True,
        )
        .first()
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
    Staff share all remaining files regardless of creator; API callers enter
    through search_for_staff to enforce the actor permission first.
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
