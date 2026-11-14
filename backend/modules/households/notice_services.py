# AI contribution: 50% or more AI-generated
"""Record a walk-in adult's income notice or non-filing reason (BR-DOC-007)."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.documents import services as document_services
from modules.households.domain.person import is_adult
from modules.households.models import Household, HouseholdDraftEvent, Member
from modules.households.policies import require_walk_in_staff
from modules.households.queries import walk_ins_for_staff


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
    require_walk_in_staff(staff_user)
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
