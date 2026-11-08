# AI contribution: 50% or more AI-generated
"""Staff permissions, file ownership and walk-in edit rules."""

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser

from modules.households.models import Household

STAFF_ROLES = frozenset(("intake_worker", "admin"))
StaffActor = AbstractBaseUser | AnonymousUser | None


def can_manage_walk_ins(actor: StaffActor) -> bool:
    """Allow only active intake workers and administrators to manage walk-ins."""
    return bool(
        actor is not None
        and actor.is_authenticated
        and actor.is_active
        and getattr(actor, "role", None) in STAFF_ROLES
    )


def is_editable_walk_in(household: Household) -> bool:
    """Only a non-anonymized walk-in draft may be edited or resumed."""
    return (
        household.channel == Household.Channel.WALK_IN
        and household.status == Household.Status.DRAFT
        and household.anonymized_at is None
    )


def can_resume_walk_in(household: Household, actor: StaffActor) -> bool:
    return bool(
        can_manage_walk_ins(actor)
        and is_editable_walk_in(household)
        and actor is not None
        and (
            getattr(actor, "role", None) == "admin"
            or household.created_by_id == actor.pk
        )
    )
