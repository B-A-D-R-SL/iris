# AI contribution: 50% or more AI-generated
"""Read-only public interfaces for walk-in household drafts."""

from uuid import UUID

from modules.households.models import Household


def walk_in_for_staff(household_id: UUID) -> Household | None:
    return (
        Household.objects.select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id, channel=Household.Channel.WALK_IN)
        .first()
    )
