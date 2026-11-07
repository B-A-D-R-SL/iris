# AI contribution: 50% or more AI-generated
"""Read-only public interfaces for household drafts and staff search."""

import re
from uuid import UUID

from django.db.models import OuterRef, QuerySet, Subquery, Value

from modules.households.models import Household, Member
from modules.households.search_expressions import SearchKey


def walk_in_for_staff(household_id: UUID) -> Household | None:
    return (
        Household.objects.select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id, channel=Household.Channel.WALK_IN)
        .first()
    )


def _matching_ids(households: QuerySet[Household], value: str) -> QuerySet:
    """UNION preserves indexable predicates and deduplicates member matches."""
    needle = SearchKey(Value(value))
    members = Member.objects.all()
    addresses = households
    keys = households
    for token in value.split():
        part = SearchKey(Value(token))
        members = members.filter(search_name_key__contains=part)
        addresses = addresses.filter(search_address_text__contains=part)
        keys = keys.filter(search_address_key__contains=part)

    branches = [
        households.filter(search_email_key__contains=needle).values("pk"),
        households.filter(search_number_key__contains=needle).values("pk"),
        addresses.values("pk"),
        keys.values("pk"),
        members.values("household_id"),
    ]
    if re.fullmatch(r"[\d\s()+.\-]+", value):
        digits = re.sub(r"\D", "", value)
        if digits:
            branches.append(households.filter(phone__contains=digits).values("pk"))

    return branches[0].union(*branches[1:])


def search(q: str) -> QuerySet[Household]:
    """Read identifying fields only, with case/accents folded by PostgreSQL.

    Input stays in bound ORM parameters, including LIKE wildcard characters.
    Anonymized files and DOB-containing duplicate keys are never searched.
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
