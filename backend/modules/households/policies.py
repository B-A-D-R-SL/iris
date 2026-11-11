# AI contribution: 50% or more AI-generated
"""Shared staff permissions and walk-in edit rules, evaluated by the backend."""

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from modules.accounts.queries import STAFF_ROLES
from modules.households.models import Household

StaffActor = AbstractBaseUser | AnonymousUser | None


def can_manage_walk_ins(actor: StaffActor) -> bool:
    """Allow only active intake workers and administrators to manage walk-ins."""
    return bool(
        actor is not None
        and actor.is_authenticated
        and actor.is_active
        and getattr(actor, "role", None) in STAFF_ROLES
    )


def can_suspend_households(actor: StaffActor) -> bool:
    """Only active administrators may change a household's suspension state."""
    return bool(
        actor is not None
        and actor.is_authenticated
        and actor.is_active
        and getattr(actor, "role", None) == "admin"
    )


def suspension_actions(household: Household, actor: StaffActor) -> list[str]:
    """Return status actions the backend currently permits for this file."""
    if not can_suspend_households(actor) or household.anonymized_at is not None:
        return []
    if household.status == Household.Status.APPROVED:
        return ["suspend"]
    if (
        household.status == Household.Status.SUSPENDED
        and household.expires_at is not None
        and household.expires_at > timezone.now()
    ):
        return ["reactivate"]
    return []


def is_editable_walk_in(household: Household) -> bool:
    """Only a non-anonymized walk-in draft may be edited or resumed."""
    return (
        household.channel == Household.Channel.WALK_IN
        and household.status == Household.Status.DRAFT
        and household.anonymized_at is None
    )


def can_resume_walk_in(household: Household, actor: StaffActor) -> bool:
    """Advertise the resume action only when the staff edit rule permits it."""
    return can_manage_walk_ins(actor) and is_editable_walk_in(household)


def can_open_household(household: Household, actor: StaffActor) -> bool:
    """Advertise the read-only household page only for visible staff files."""
    return can_manage_walk_ins(actor) and household.anonymized_at is None
