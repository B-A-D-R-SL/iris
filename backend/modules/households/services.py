# AI contribution: 50% or more AI-generated
"""Create, edit, submit and approve walk-in files, and record their notices, for staff."""

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
from django.db.models import QuerySet
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.audit import services as audit_services
from modules.documents import services as document_services
from modules.households import _approval
from modules.households.domain.person import is_adult
from modules.households.exceptions import DuplicateLockTimeout
from modules.households.limits import max_household_people
from modules.households.models import Household, HouseholdDraftEvent, Member
from modules.households.policies import (
    can_manage_walk_ins,
    can_suspend_households,
    is_editable_walk_in,
)
from modules.households.queries import (
    find_possible_duplicates,
    require_adult_notices,
    walk_ins_for_staff,
)
from modules.notifications import services as notification_services
from modules.privacy import services as privacy_services
from modules.reservations import services as reservation_services
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.households")

# BR-DUP-002: approval is a separate step after submission (duplicate check).
APPROVABLE = frozenset({Household.Status.SUBMITTED, Household.Status.REVIEW_REQUIRED})

ADDRESS_FIELDS = frozenset(
    ("street_number", "street_name", "unit", "city", "postal_code")
)
MEMBER_FIELDS = frozenset(("first_name", "last_name", "date_of_birth"))
CONSENT_TEXT_VERSION = "2026-11-v1"
POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"


def _status_reason(reason: str) -> str:
    """Normalize a reason and enforce the active privacy and length rules."""
    value = " ".join(reason.split())
    if not value:
        raise ValidationError({"reason": _("Enter a reason.")})
    limit = rule_queries.household_suspension_reason_max_length()
    if len(value) > limit:
        raise ValidationError(
            {"reason": _("Enter at most %(limit)s characters.") % {"limit": limit}}
        )
    if privacy_services.household_reason_contains_sensitive_data(value):
        raise ValidationError(
            {"reason": _("Do not include personal or financial information.")}
        )
    return value


def _locked_status_household(household_id: UUID, reactivate: bool) -> Household:
    """Lock a visible file and validate the requested source state."""
    household = (
        Household.objects.select_for_update()
        .filter(pk=household_id, anonymized_at__isnull=True)
        .first()
    )
    if household is None:
        raise Household.DoesNotExist
    expected = Household.Status.SUSPENDED if reactivate else Household.Status.APPROVED
    if household.status != expected:
        message = (
            _("Only suspended household files can be reactivated.")
            if reactivate
            else _("Only approved household files can be suspended.")
        )
        raise ValidationError({"status": message})
    if reactivate and (
        household.expires_at is None or household.expires_at <= timezone.now()
    ):
        raise ValidationError({"status": _("An expired file cannot be reactivated.")})
    return household


def _save_status(household: Household, reason: str, reactivate: bool) -> str:
    """Persist the new status and return its audit action."""
    action = "reactivate" if reactivate else "suspend"
    household.status = (
        Household.Status.APPROVED if reactivate else Household.Status.SUSPENDED
    )
    household.status_reason = "" if reactivate else reason
    household.full_clean()
    household.save(update_fields=("status", "status_reason", "updated_at"))
    return action


@transaction.atomic
def change_suspension(
    household_id: UUID,
    reason: str,
    actor: AbstractBaseUser,
    *,
    reactivate: bool,
) -> Household:
    """Suspend an approved file or reactivate a suspended file while valid."""
    if not can_suspend_households(actor):
        raise PermissionDenied(_("Only active administrators can change suspension."))
    clean_reason = _status_reason(reason)
    household = _locked_status_household(household_id, reactivate)
    action = _save_status(household, clean_reason, reactivate)
    if not reactivate:
        reservation_services.cancel_open_for_household(household.pk)
    audit_services.record(
        actor, action, "household", household.pk, {"reason": clean_reason}
    )
    notification_services.queue_household_status_email(
        email=household.email,
        language=household.preferred_language,
        status=household.status,
        reason=clean_reason,
    )
    return household


@transaction.atomic
def approve_walk_in(household: Household, staff: AbstractBaseUser) -> Household:
    _require_staff(staff)
    if getattr(staff, "pk", None) is None or getattr(
        getattr(staff, "_state", None), "adding", True
    ):
        raise PermissionDenied(
            _("Only active intake workers and admins can manage walk-ins.")
        )
    # Draft editing and notice entry take this same lock before changing evidence.
    locked = Household.objects.select_for_update().get(
        pk=household.pk,
        channel=Household.Channel.WALK_IN,
        anonymized_at__isnull=True,
    )
    if locked.status == Household.Status.DRAFT:
        # BR-DUP-002: approval follows submission, which runs the duplicate check.
        raise ValidationError(_("Submit the file before approving it."))
    if locked.status not in APPROVABLE:
        raise ValidationError(
            _("This household file cannot be approved in its current status.")
        )
    locked.full_clean()
    _approval.check_complete(locked)
    _approval.apply_outcome(locked, staff)
    _approval.record_outcome(locked, staff)
    return locked


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


def _same_person(member: Member, values: Mapping[str, Any]) -> bool:
    return (
        member.first_name == str(values.get("first_name", "")).strip()
        and member.last_name == str(values.get("last_name", "")).strip()
        and member.date_of_birth == values.get("date_of_birth")
        and member.relation == values.get("relation")
    )


def _unchanged_members(
    household: Household, members: list[dict[str, Any]]
) -> tuple[set[UUID], list[dict[str, Any]]]:
    """Ids of existing members sent back unchanged, and the entries that are new."""
    existing = list(household.members.exclude(relation=Member.Relation.HOLDER))
    kept: set[UUID] = set()
    new_members: list[dict[str, Any]] = []
    for values in members:
        match = next(
            (m for m in existing if m.pk not in kept and _same_person(m, values)),
            None,
        )
        if match is None:
            new_members.append(values)
        else:
            kept.add(match.pk)
    return kept, new_members


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
    if any(values.get("relation") == Member.Relation.HOLDER for values in members):
        raise ValidationError({"members": _("The holder is added automatically.")})
    # Members sent back unchanged keep their row, so their notices stay linked;
    # only removed or changed members are deleted (refused if they have notices).
    kept, new_members = _unchanged_members(household, members)
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
    for values in new_members:
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


def _notice_member(household: Household, data: Mapping[str, Any]) -> Member:
    """BR-DOC-007: the adult of this draft walk-in that the notice is for."""
    if household.status != Household.Status.DRAFT:
        raise ValidationError(
            {"status": _("Notices can only be added to a draft file.")}
        )
    member_id = data.get("member")
    member = (
        household.members.filter(pk=member_id).first()
        if isinstance(member_id, UUID)
        else None
    )
    if member is None:
        raise ValidationError({"member": _("Choose a person from this household.")})
    if not is_adult(member.date_of_birth, timezone.localdate()):
        raise ValidationError({"member": _("Notices are recorded for adults only.")})
    return member


def record_walk_in_notice(
    household_id: UUID, data: Mapping[str, Any], staff_user: AbstractBaseUser
) -> document_services.IncomeNotice:
    """Record an adult's notice or non-filing reason on a draft walk-in (BR-DOC-007).

    The file is checked and stored first, with no lock held, so a slow upload never
    blocks draft edits or approval of this file. The row is then locked, the draft
    and member checked again, and the notice saved; on failure the file is removed.
    """
    _require_staff(staff_user)
    # Same scope as every walk-in path: walk-in channel, not anonymized.
    files = walk_ins_for_staff(staff_user)
    _notice_member(files.get(pk=household_id), data)  # nothing is stored if refused
    values = {
        key: value for key, value in data.items() if key not in ("member", "file")
    }
    prepared = document_services.prepare_staff_notice(
        values, data.get("file"), staff_user
    )
    try:
        return _save_walk_in_notice(files, household_id, data, staff_user, prepared)
    except Exception:
        document_services.discard_prepared_notice(prepared)
        raise


@transaction.atomic
def _save_walk_in_notice(
    files: QuerySet[Household],
    household_id: UUID,
    data: Mapping[str, Any],
    staff_user: AbstractBaseUser,
    prepared: document_services.PreparedNotice,
) -> document_services.IncomeNotice:
    # Draft edits and approval take this lock too, so the checks hold until saved.
    household = files.select_for_update().get(pk=household_id)
    member = _notice_member(household, data)
    HouseholdDraftEvent.objects.create(
        household=household,
        actor_id=staff_user.pk,
        actor_role=getattr(staff_user, "role", ""),
        action=HouseholdDraftEvent.Action.UPDATED,
    )
    return document_services.save_prepared_notice(member.pk, prepared, staff_user)


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
        require_adult_notices(household)
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
