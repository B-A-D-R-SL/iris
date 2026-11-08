# AI contribution: 50% or more AI-generated
"""Read household files and find possible duplicates."""

from uuid import UUID

from django.db.models import Q, QuerySet
from django.utils import timezone

from modules.households.models import Household, Member

DUPLICATE_CANDIDATE_STATUSES = (
    Household.Status.SUBMITTED,
    Household.Status.REVIEW_REQUIRED,
    Household.Status.AWAITING_VISIT,
    Household.Status.APPROVED,
    Household.Status.RENEWAL_NEEDED,
    Household.Status.SUSPENDED,
)


def walk_in_for_staff(household_id: UUID) -> Household | None:
    return (
        Household.objects.select_related("created_by", "verified_by")
        .prefetch_related("members")
        .filter(pk=household_id, channel=Household.Channel.WALK_IN)
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
