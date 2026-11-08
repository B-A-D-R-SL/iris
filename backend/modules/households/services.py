# AI contribution: 50% or more AI-generated
"""Create, edit and submit walk-in files for staff."""

import hashlib
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.households.limits import max_household_people
from modules.households.models import Household, HouseholdDraftEvent, Member
from modules.households.queries import find_possible_duplicates

STAFF_ROLES = frozenset(("intake_worker", "admin"))
ADDRESS_FIELDS = frozenset(
    ("street_number", "street_name", "unit", "city", "postal_code")
)
MEMBER_FIELDS = frozenset(("first_name", "last_name", "date_of_birth"))
CONSENT_TEXT_VERSION = "2026-11-v1"
POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"


def _require_staff(user: AbstractBaseUser) -> None:
    if (
        not user.is_authenticated
        or not user.is_active
        or getattr(user, "role", None) not in STAFF_ROLES
    ):
        raise PermissionDenied(
            _("Only active intake workers and admins can manage walk-ins.")
        )


def _apply_holder(household: Household, values: Mapping[str, Any]) -> None:
    if "phone" in values:
        household.phone = values["phone"]
    if "email" in values:
        household.email = values["email"] or None
    if "preferred_language" in values:
        household.preferred_language = values["preferred_language"]


def _apply_address(household: Household, values: Mapping[str, Any]) -> None:
    for name in ADDRESS_FIELDS & values.keys():
        setattr(household, name, values[name] or "")


def _apply_verification(
    household: Household, verified: bool, actor: AbstractBaseUser
) -> None:
    """Keep the original verification time when the answer is unchanged."""
    if verified == household.identity_checked_in_person:
        return
    household.identity_checked_in_person = verified
    household.verified_by_id = actor.pk if verified else None
    household.verified_at = timezone.now() if verified else None


def _apply_consent(household: Household, given: bool) -> None:
    """Keep the first consent time when consent is sent again."""
    if not given:
        household.consent_data_processing_at = None
        household.consent_text_version = ""
    elif household.consent_data_processing_at is None:
        household.consent_data_processing_at = timezone.now()
        household.consent_text_version = CONSENT_TEXT_VERSION


def _save_member(
    household: Household,
    values: Mapping[str, Any],
    relation: str,
    member: Member | None = None,
) -> Member:
    if member is None:
        member = Member(household=household, relation=relation)
    for field in MEMBER_FIELDS & values.keys():
        setattr(member, field, values[field])
    member.full_clean()
    member.save()
    return member


def _replace_other_members(household: Household, members: list[dict[str, Any]]) -> None:
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
    try:
        household.members.exclude(relation=Member.Relation.HOLDER).delete()
    except ProtectedError as exc:
        raise ValidationError(
            {
                "members": _(
                    "Cannot replace members already linked to notices or other records."
                )
            }
        ) from exc
    for values in members:
        if values.get("relation") == Member.Relation.HOLDER:
            raise ValidationError({"members": _("The holder is added automatically.")})
        member = Member(household=household, **values)
        member.full_clean()
        member.save()


@transaction.atomic
def create_walk_in(data: Mapping[str, Any], staff_user: AbstractBaseUser) -> Household:
    """The holder is automatically member one."""
    _require_staff(staff_user)
    holder = data.get("holder")
    if not isinstance(holder, Mapping) or not MEMBER_FIELDS.issubset(holder):
        raise ValidationError(
            {"holder": _("Enter the holder's name and date of birth.")}
        )
    if not holder.get("phone"):
        raise ValidationError({"holder": _("Enter the holder's telephone number.")})

    household = Household(
        channel=Household.Channel.WALK_IN,
        status=Household.Status.DRAFT,
        created_by_id=staff_user.pk,
        phone=holder["phone"],
    )
    _apply_holder(household, holder)
    _apply_address(household, data.get("address", {}))
    if "identity_checked_in_person" in data:
        _apply_verification(household, data["identity_checked_in_person"], staff_user)
    if "consent_data_processing" in data:
        _apply_consent(household, data["consent_data_processing"])
    household.full_clean()
    household.save()
    _save_member(household, holder, Member.Relation.HOLDER)
    if "members" in data:
        _replace_other_members(household, data["members"])
    HouseholdDraftEvent.objects.create(
        household=household,
        actor_id=staff_user.pk,
        actor_role=getattr(staff_user, "role", ""),
        action=HouseholdDraftEvent.Action.CREATED,
    )
    return household


@transaction.atomic
def update_draft(
    household_id: UUID, data: Mapping[str, Any], staff_user: AbstractBaseUser
) -> Household:
    """Patch a draft atomically; non-draft files are never editable here."""
    _require_staff(staff_user)
    if not data:
        raise ValidationError({"non_field_errors": _("Provide at least one change.")})
    household = Household.objects.select_for_update().get(
        id=household_id, channel=Household.Channel.WALK_IN
    )
    if household.status != Household.Status.DRAFT:
        raise ValidationError(
            {"status": _("Only draft household files can be edited.")}
        )
    holder = data.get("holder")
    if holder is not None:
        _apply_holder(household, holder)
    if "address" in data:
        _apply_address(household, data["address"])
    if "identity_checked_in_person" in data:
        _apply_verification(household, data["identity_checked_in_person"], staff_user)
    if "consent_data_processing" in data:
        _apply_consent(household, data["consent_data_processing"])
    household.full_clean()
    household.save()
    if holder is not None and MEMBER_FIELDS & holder.keys():
        # Files seeded by SET-18 have no holder member yet: create it when complete.
        holder_member = household.members.filter(
            relation=Member.Relation.HOLDER
        ).first()
        if holder_member is None and not MEMBER_FIELDS.issubset(holder):
            raise ValidationError(
                {"holder": _("Enter the holder's name and date of birth.")}
            )
        _save_member(household, holder, Member.Relation.HOLDER, holder_member)
    if "members" in data:
        _replace_other_members(household, data["members"])
    HouseholdDraftEvent.objects.create(
        household=household,
        actor_id=staff_user.pk,
        actor_role=getattr(staff_user, "role", ""),
        action=HouseholdDraftEvent.Action.UPDATED,
    )
    return household


def _submission_members(household: Household) -> list[Member]:
    if household.anonymized_at is not None:
        raise ValidationError({"status": _("An anonymized file cannot be submitted.")})
    household.full_clean()
    if not household.address_key:
        raise ValidationError({"address": _("Complete the address before submission.")})
    if not household.identity_checked_in_person:
        raise ValidationError(
            {"identity_checked_in_person": _("Staff verification is required.")}
        )
    if not household.consent_data_processing_at or not household.consent_text_version:
        raise ValidationError(
            {"consent_data_processing": _("Data-processing consent is required.")}
        )
    members = list(household.members.order_by("pk"))
    if sum(member.relation == Member.Relation.HOLDER for member in members) != 1:
        raise ValidationError(
            {"holder": _("Enter the holder's name and date of birth.")}
        )
    limit = max_household_people()
    if len(members) > limit:
        raise ValidationError(
            {
                "members": _(
                    "A household can have at most %(limit)s people including the holder."
                )
                % {"limit": limit}
            }
        )
    for member in members:
        member.full_clean()
    return members


def _lock_duplicate_keys(household: Household, members: list[Member]) -> None:
    """Lock shared addresses and people until the transaction ends."""
    keys = [f"address:{household.address_key}"]
    keys.extend(f"person:{member.person_key}" for member in members)
    # Use the same lock numbers and order in every worker to avoid deadlocks.
    lock_ids = sorted(
        {
            int.from_bytes(
                hashlib.sha256(f"households:duplicates:{key}".encode()).digest()[:8],
                signed=True,
            )
            for key in keys
        }
    )
    with connection.cursor() as cursor:
        for lock_id in lock_ids:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])


@transaction.atomic
def submit_walk_in(household_id: UUID, staff_user: AbstractBaseUser) -> Household:
    """Submit a draft or send a possible duplicate for review."""
    _require_staff(staff_user)
    # Block draft edits while this submission runs.
    household = Household.objects.select_for_update().get(
        pk=household_id, channel=Household.Channel.WALK_IN
    )
    if household.status != Household.Status.DRAFT:
        raise ValidationError(
            {"status": _("Only draft household files can be submitted.")}
        )
    members = _submission_members(household)
    _lock_duplicate_keys(household, members)
    # Save the keys rebuilt by full_clean().
    for member in members:
        member.save(update_fields=["person_key"])
    duplicate = find_possible_duplicates(household).exists()
    household.status = (
        Household.Status.REVIEW_REQUIRED if duplicate else Household.Status.SUBMITTED
    )
    household.status_reason = POSSIBLE_DUPLICATE if duplicate else ""
    household.submitted_at = timezone.now()
    household.save()
    return household
