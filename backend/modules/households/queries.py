# AI contribution: 50% or more AI-generated
"""Read-only public interfaces for household files."""

from datetime import datetime
from uuid import UUID

from modules.households.models import Household


def walk_in_for_staff(household_id: UUID) -> Household | None:
    return (
        Household.objects.select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id, channel=Household.Channel.WALK_IN)
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
