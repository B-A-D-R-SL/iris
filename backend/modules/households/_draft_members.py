# AI contribution: 50% or more AI-generated
"""Save members within the walk-in draft transaction."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.documents.queries import has_income_notices
from modules.households.domain.person import is_adult
from modules.households.limits import max_household_people
from modules.households.models import Household, Member

MEMBER_FIELDS = frozenset(("first_name", "last_name", "date_of_birth"))


def save_member(
    household: Household,
    values: Mapping[str, Any],
    relation: str,
    member: Member | None = None,
) -> Member:
    if member is None:
        member = Member(household=household)
    member.relation = relation
    for field in MEMBER_FIELDS & values.keys():
        setattr(member, field, values[field])
    member.full_clean()
    member.save()
    return member


def _same_person(member: Member, values: Mapping[str, Any]) -> bool:
    return (
        member.first_name == str(values.get("first_name", "")).strip()
        and member.last_name == str(values.get("last_name", "")).strip()
        and member.date_of_birth == values.get("date_of_birth")
        and member.relation == values.get("relation")
    )


def _plan_member_edits(
    household: Household, members: list[dict[str, Any]]
) -> tuple[set[UUID], list[tuple[Member | None, dict[str, Any]]]]:
    existing = {
        member.pk: member
        for member in household.members.exclude(relation=Member.Relation.HOLDER)
    }
    ids = [values["id"] for values in members if "id" in values]
    kept = set(ids)
    if len(kept) != len(ids):
        raise ValidationError({"members": _("Send each household member only once.")})
    if kept - existing.keys():
        raise ValidationError(
            {"members": _("Choose a household member other than the holder.")}
        )

    pending: list[tuple[Member | None, dict[str, Any]]] = []
    today = timezone.localdate()
    for values in members:
        if "id" in values:
            member = existing[values["id"]]
            birth = values["date_of_birth"]
            if (
                birth != member.date_of_birth
                and not is_adult(birth, today)
                and has_income_notices(member.pk)
            ):
                raise ValidationError(
                    {"members": _("A member with a notice must be at least 18.")}
                )
            if not _same_person(member, values):
                pending.append((member, values))
            continue

        # Older clients can still keep an unchanged member without sending an ID.
        match = next(
            (
                member
                for member in existing.values()
                if member.pk not in kept and _same_person(member, values)
            ),
            None,
        )
        if match is None:
            pending.append((None, values))
        else:
            kept.add(match.pk)
    return kept, pending


def replace_other_members(household: Household, members: list[dict[str, Any]]) -> None:
    limit = max_household_people()
    if len(members) > limit - 1:
        raise ValidationError(
            {
                "members": _(
                    "A household can have at most %(limit)s people including the holder."
                )
                % {"limit": limit}
            }
        )
    if any(values.get("relation") == Member.Relation.HOLDER for values in members):
        raise ValidationError({"members": _("The holder is added automatically.")})
    kept, pending = _plan_member_edits(household, members)
    try:
        household.members.exclude(relation=Member.Relation.HOLDER).exclude(
            pk__in=kept
        ).delete()
    except ProtectedError as exc:
        raise ValidationError(
            {
                "members": _(
                    "Cannot replace members already linked to notices or other records."
                )
            }
        ) from exc
    for member, values in pending:
        save_member(household, values, values["relation"], member)
