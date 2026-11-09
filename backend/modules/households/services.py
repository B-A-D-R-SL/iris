# AI contribution: 50% or more AI-generated
"""Create, edit and submit walk-in files for staff."""

import hashlib
import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.households.exceptions import DuplicateLockTimeout
from modules.households.limits import max_household_people
from modules.households.models import Household, HouseholdDraftEvent, Member
from modules.households.policies import can_manage_walk_ins, is_editable_walk_in
from modules.households.queries import find_possible_duplicates, walk_ins_for_staff

logger = logging.getLogger("iris.households")

ADDRESS_FIELDS = frozenset(
    ("street_number", "street_name", "unit", "city", "postal_code")
)
MEMBER_FIELDS = frozenset(("first_name", "last_name", "date_of_birth"))
CONSENT_TEXT_VERSION = "2026-11-v1"
POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"


def _require_staff(user: AbstractBaseUser) -> None:
    if not can_manage_walk_ins(user):
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
    household = walk_ins_for_staff(staff_user).select_for_update().get(pk=household_id)
    if not data:
        raise ValidationError({"non_field_errors": _("Provide at least one change.")})
    if not is_editable_walk_in(household):
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
        cursor.execute("SHOW lock_timeout")
        previous_timeout = cursor.fetchone()[0]
        cursor.execute(
            "SELECT set_config('lock_timeout', %s, true)",
            [f"{settings.HOUSEHOLD_DUPLICATE_LOCK_TIMEOUT_MS}ms"],
        )
        for lock_id in lock_ids:
            try:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
            except OperationalError as exc:
                if getattr(exc.__cause__, "sqlstate", None) != "55P03":
                    raise
                logger.warning(
                    "Household duplicate lock timed out",
                    extra={"event": "household_duplicate_lock_timeout"},
                )
                raise DuplicateLockTimeout from exc
        # Leave later work in an outer transaction under its original timeout.
        cursor.execute(
            "SELECT set_config('lock_timeout', %s, true)", [previous_timeout]
        )


@contextmanager
def locked_duplicate_check(
    household_id: UUID, staff_user: AbstractBaseUser
) -> Iterator[tuple[Household, bool]]:
    """Hold submission locks while the caller saves the checked draft."""
    with transaction.atomic():
        _require_staff(staff_user)
        household = (
            walk_ins_for_staff(staff_user).select_for_update().get(pk=household_id)
        )
        if household.status != Household.Status.DRAFT:
            raise ValidationError(
                {"status": _("Only draft household files can be submitted.")}
            )
        members = _submission_members(household)
        _lock_duplicate_keys(household, members)
        for member in members:
            member.save(update_fields=["person_key"])
        yield household, find_possible_duplicates(household).exists()


def submit_walk_in(household_id: UUID, staff_user: AbstractBaseUser) -> Household:
    """Submit a draft or send a possible duplicate for review."""
    with locked_duplicate_check(household_id, staff_user) as (household, duplicate):
        household.status = (
            Household.Status.REVIEW_REQUIRED
            if duplicate
            else Household.Status.SUBMITTED
        )
        household.status_reason = POSSIBLE_DUPLICATE if duplicate else ""
        household.submitted_at = timezone.now()
        household.save()
        HouseholdDraftEvent.objects.create(
            household=household,
            actor_id=staff_user.pk,
            actor_role=getattr(staff_user, "role", ""),
            action=HouseholdDraftEvent.Action.SUBMITTED,
        )
        event = "household_duplicate_review" if duplicate else "household_submitted"
        transaction.on_commit(lambda: logger.info(event, extra={"event": event}))
    return household
