# AI contribution: 50% or more AI-generated
"""Staff-only transactional creation and editing of walk-in household drafts and notices."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.accounts.queries import is_intake_staff
from modules.documents import services as document_services
from modules.households.domain.person import is_adult
from modules.households.models import Household, HouseholdDraftEvent, Member

ADDRESS_FIELDS = frozenset(
    ("street_number", "street_name", "unit", "city", "postal_code")
)
MEMBER_FIELDS = frozenset(("first_name", "last_name", "date_of_birth"))
# Version of the data-processing consent text read to the person.
CONSENT_TEXT_VERSION = "2026-11-v1"


def _require_staff(user: AbstractBaseUser) -> None:
    if not is_intake_staff(user):
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
    """Record who checked the ID and when; re-sending the same answer changes nothing."""
    if verified == household.identity_checked_in_person:
        return
    household.identity_checked_in_person = verified
    household.verified_by_id = actor.pk if verified else None
    household.verified_at = timezone.now() if verified else None


def _apply_consent(household: Household, given: bool) -> None:
    """Store when consent was given and which text; keep the first time if re-sent."""
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
    if len(members) > 14:
        raise ValidationError(
            {
                "members": _(
                    "A household can have at most 15 people including the holder."
                )
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
    """Create a resumable walk-in draft. The holder is automatically member one."""
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


@transaction.atomic
def record_walk_in_notice(
    household_id: UUID, data: Mapping[str, Any], staff_user: AbstractBaseUser
) -> document_services.IncomeNotice:
    """Record an adult's notice or non-filing reason on a draft walk-in (BR-DOC-007).

    The household row stays locked until the notice is saved, so two staff
    entries for the same file cannot interleave. documents is called last.
    """
    _require_staff(staff_user)
    household = Household.objects.select_for_update().get(
        id=household_id, channel=Household.Channel.WALK_IN
    )
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
    HouseholdDraftEvent.objects.create(
        household=household,
        actor_id=staff_user.pk,
        actor_role=getattr(staff_user, "role", ""),
        action=HouseholdDraftEvent.Action.UPDATED,
    )
    values = {
        key: value for key, value in data.items() if key not in ("member", "file")
    }
    return document_services.record_staff_notice(
        member.pk, values, data.get("file"), staff_user
    )
