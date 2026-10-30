# AI contribution: 50% or more AI-generated
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction

from modules.audit.models import AuditEvent


@transaction.atomic
def record(
    actor: AbstractBaseUser,
    action: str,
    target_type: str,
    target_id: str | int | UUID,
    metadata: dict[str, str],
) -> AuditEvent:
    if not isinstance(actor, get_user_model()) or actor._state.adding:
        raise ValidationError({"actor": "A saved user is required."})
    role = actor._meta.get_field("role").clean(getattr(actor, "role", None), actor)
    if not isinstance(target_id, (str, int, UUID)) or isinstance(target_id, bool):
        raise ValidationError({"target_id": "A record identifier is required."})
    if not str(target_id).strip():
        raise ValidationError({"target_id": "A record identifier is required."})
    if (
        not isinstance(metadata, dict)
        or metadata.keys() - {"outcome"}
        or (
            "outcome" in metadata
            and metadata["outcome"] not in ("approved", "rejected", "review_required")
        )
    ):
        raise ValidationError({"metadata": "Only a supported outcome is allowed."})

    event = AuditEvent(
        actor=actor,
        actor_role=role,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        metadata=metadata,
    )
    event.full_clean()
    event.save()
    return event
