# AI contribution: 50% or more AI-generated
"""Read-only public interfaces for walk-in household drafts."""

from uuid import UUID

from modules.households.domain.names import short_full_name, short_name
from modules.households.models import Household, Member


def walk_in_for_staff(household_id: UUID) -> Household | None:
    return (
        Household.objects.select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id, channel=Household.Channel.WALK_IN)
        .first()
    )


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
