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
    metadata: dict[str, str | int],
) -> AuditEvent:
    """Record a validated event in the caller's transaction."""
    if not isinstance(actor, get_user_model()) or actor._state.adding:
        raise ValidationError({"actor": "A saved user is required."})
    role = actor._meta.get_field("role").clean(getattr(actor, "role", None), actor)
    if not isinstance(target_id, (str, int, UUID)) or isinstance(target_id, bool):
        raise ValidationError({"target_id": "A record identifier is required."})
    if not str(target_id).strip():
        raise ValidationError({"target_id": "A record identifier is required."})
    if action == "rule_published" and target_type == "rule_set_version":
        valid_metadata = (
            isinstance(metadata, dict)
            and set(metadata) == {"rule_type", "version"}
            and isinstance(metadata["rule_type"], str)
            and metadata["rule_type"] in _rule_types()
            and type(metadata["version"]) is int
            and metadata["version"] > 0
        )
    else:
        valid_metadata = (
            isinstance(metadata, dict)
            and not (metadata.keys() - {"outcome"})
            and (
                "outcome" not in metadata
                or metadata["outcome"] in ("approved", "rejected", "review_required")
            )
        )
    if not valid_metadata or (
        action == "rule_published" and target_type != "rule_set_version"
    ):
        raise ValidationError({"metadata": "Unsupported audit metadata."})

    target_identifier = str(target_id)
    if target_type == "household":
        try:
            target_identifier = str(UUID(target_identifier))
        except ValueError:
            pass

    event = AuditEvent(
        actor=actor,
        actor_role=role,
        action=action,
        target_type=target_type,
        target_id=target_identifier,
        metadata=metadata,
    )
    event.full_clean()
    event.save()
    return event


def _rule_types() -> set[str]:
    # Import the public rules interface lazily to avoid module initialization cycles.
    from modules.rules.services import supported_rule_types

    return supported_rule_types()
