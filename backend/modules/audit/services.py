# AI contribution: 50% or more AI-generated
from collections.abc import Iterable
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction

from modules.audit.models import AuditEvent


def _actor_role(actor: AbstractBaseUser) -> str:
    if not isinstance(actor, get_user_model()) or actor._state.adding:
        raise ValidationError({"actor": "A saved user is required."})
    return str(actor._meta.get_field("role").clean(getattr(actor, "role", None), actor))


def _target_identifier(target_type: str, target_id: str | int | UUID) -> str:
    if not isinstance(target_id, (str, int, UUID)) or isinstance(target_id, bool):
        raise ValidationError({"target_id": "A record identifier is required."})
    if not str(target_id).strip():
        raise ValidationError({"target_id": "A record identifier is required."})
    identifier = str(target_id)
    if target_type == "household":
        try:
            identifier = str(UUID(identifier))
        except ValueError:
            pass
    return identifier


def _validate_metadata(metadata: dict[str, str]) -> None:
    if (
        not isinstance(metadata, dict)
        or metadata.keys() - {"outcome"}
        or (
            "outcome" in metadata
            and metadata["outcome"] not in ("approved", "rejected", "review_required")
        )
    ):
        raise ValidationError({"metadata": "Only a supported outcome is allowed."})


@transaction.atomic
def record(
    actor: AbstractBaseUser,
    action: str,
    target_type: str,
    target_id: str | int | UUID,
    metadata: dict[str, str],
) -> AuditEvent:
    """Record a validated event with outcome-only metadata in the caller's transaction."""
    role = _actor_role(actor)
    _validate_metadata(metadata)
    event = AuditEvent(
        actor_id=actor.pk,
        actor_role=role,
        action=action,
        target_type=target_type,
        target_id=_target_identifier(target_type, target_id),
        metadata=metadata,
    )
    event.full_clean()
    event.save()
    return event


def record_household_views(
    actor: AbstractBaseUser, household_ids: Iterable[UUID]
) -> list[AuditEvent]:
    """Append one event per disclosed file with a single INSERT for search pages.

    The actor/role and UUID inputs are validated once, and PostgreSQL enforces
    the FK. All remaining fields are fixed valid values, so this path cannot
    accept arbitrary actions, target types, metadata or identifying details.
    """
    role = _actor_role(actor)
    events = []
    for identifier in household_ids:
        if not isinstance(identifier, UUID):
            raise ValidationError({"target_id": "A household UUID is required."})
        event = AuditEvent(
            actor_id=actor.pk,
            actor_role=role,
            action="view",
            target_type="household",
            target_id=str(identifier),
            metadata={},
        )
        events.append(event)
    return list(AuditEvent.objects.bulk_create(events))
