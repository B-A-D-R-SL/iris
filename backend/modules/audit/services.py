# AI contribution: 50% or more AI-generated
from collections.abc import Iterable
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import transaction

from modules.audit.models import AuditEvent
from modules.privacy import services as privacy_services
from modules.rules import queries as rule_queries


def _actor_role(actor: AbstractBaseUser) -> str:
    """Require a persisted account and capture its validated role for the event."""
    if not isinstance(actor, get_user_model()) or actor._state.adding:
        raise ValidationError({"actor": "A saved user is required."})
    return str(actor._meta.get_field("role").clean(getattr(actor, "role", None), actor))


def _target_identifier(target_type: str, target_id: str | int | UUID) -> str:
    """Reject empty targets and canonicalize household UUIDs for audit searches."""
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


# Closed identifiers prevent arbitrary personal data in audit metadata. Keep in
# sync with rules schemas; the integration tests check the two contracts.
RULE_PUBLICATION_TYPES = frozenset(
    {
        "household_size",
        "household_suspension",
        "invitations",
        "lico_thresholds",
        "auto_approval",
        "priority",
        "tiers",
        "strikes",
        "reservations",
        "listing_safety",
        "listing_posting",
        "notice_upload",
        "file_validity",
        "retention",
    }
)


def _validate_rule_publication(
    target_type: str, metadata: dict[str, str | int]
) -> None:
    """Require a supported rule type and a positive publication version."""
    valid = (
        target_type == "rule_set_version"
        and set(metadata) == {"rule_type", "version"}
        and isinstance(metadata["rule_type"], str)
        and metadata["rule_type"] in RULE_PUBLICATION_TYPES
        and type(metadata["version"]) is int
        and metadata["version"] > 0
    )
    if not valid:
        raise ValidationError({"metadata": "Unsupported audit metadata."})


def _validate_metadata(
    action: str, target_type: str, metadata: dict[str, str | int]
) -> None:
    """Accept only the fields defined for each audit action."""
    if not isinstance(metadata, dict):
        raise ValidationError({"metadata": "Audit metadata must be an object."})
    if action == AuditEvent.Action.RULE_PUBLISHED:
        _validate_rule_publication(target_type, metadata)
        return
    if action == AuditEvent.Action.DECISION:
        if not metadata:
            return
        if set(metadata) != {"outcome"} or metadata["outcome"] not in (
            "approved",
            "rejected",
            "review_required",
        ):
            raise ValidationError({"metadata": "A supported outcome is required."})
        return
    if action in (AuditEvent.Action.SUSPEND, AuditEvent.Action.REACTIVATE):
        reason = metadata.get("reason")
        if set(metadata) != {"reason"} or not isinstance(reason, str) or not reason:
            raise ValidationError({"metadata": "A reason is required."})
        if len(reason) > rule_queries.household_suspension_reason_max_length():
            raise ValidationError({"metadata": "The reason is too long."})
        if privacy_services.household_reason_contains_sensitive_data(reason):
            raise ValidationError({"metadata": "Sensitive reasons are not allowed."})
        return
    if metadata:
        raise ValidationError({"metadata": "This action does not accept metadata."})


@transaction.atomic
def record(
    actor: AbstractBaseUser,
    action: str,
    target_type: str,
    target_id: str | int | UUID,
    metadata: dict[str, str | int],
) -> AuditEvent:
    """Record a validated event in the caller's transaction."""
    role = _actor_role(actor)
    _validate_metadata(action, target_type, metadata)
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
