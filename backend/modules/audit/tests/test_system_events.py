# AI contribution: 50% or more AI-generated
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import translation

from modules.audit import services
from modules.audit.models import AuditEvent


@pytest.mark.parametrize(
    "action,metadata",
    [
        ("view", {}),
        ("create", {}),
        ("update", {}),
        ("submit", {}),
        ("decision", {}),
        ("decision", {"outcome": "approved"}),
    ],
)
def test_null_actor_is_rejected_for_non_system_events(event_inputs, action, metadata):
    event_inputs.update(actor=None, action=action, metadata=metadata)
    with pytest.raises(ValidationError, match="actor"):
        services.record(**event_inputs)
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize(
    "mismatch",
    ["missing", "staff", "household", "invalid_household", "outcome", "rule"],
)
def test_system_event_must_match_a_saved_automatic_decision(
    system_inputs, automatic_decision, actor, mismatch
):
    if mismatch == "missing":
        system_inputs["metadata"]["decision_id"] = str(uuid4())
    elif mismatch == "staff":
        # A distinct, valid staff decision cannot be relabelled as automatic.
        model = type(automatic_decision)
        values = {
            field.attname: getattr(automatic_decision, field.attname)
            for field in model._meta.fields
            if field.name not in {"id", "created_at", "decided_by", "decided_by_type"}
        }
        decision = model.objects.create(
            **values, decided_by=actor, decided_by_type="staff"
        )
        system_inputs["metadata"]["decision_id"] = str(decision.pk)
    elif mismatch == "household":
        system_inputs["target_id"] = uuid4()
    elif mismatch == "invalid_household":
        system_inputs["target_id"] = "external-id"
    elif mismatch == "outcome":
        system_inputs["metadata"]["outcome"] = "ineligible"
    else:
        system_inputs["metadata"]["rule_version"] += 1
    before = AuditEvent.objects.count()
    with pytest.raises(ValidationError, match="actor"):
        services.record(**system_inputs)
    assert AuditEvent.objects.count() == before


@pytest.mark.parametrize("method", ["create", "bulk_create", "sql"])
@pytest.mark.parametrize(
    "has_actor,role,action,target_type",
    [
        (False, "admin", "decision", "household"),
        (False, "intake_worker", "view", "household"),
        (False, "system", "view", "household"),
        (False, "system", "decision", "external_record"),
        (True, "system", "decision", "household"),
    ],
)
def test_database_rejects_inconsistent_system_actors(
    event_inputs, method, has_actor, role, action, target_type
):
    values = {
        **event_inputs,
        "actor": event_inputs["actor"] if has_actor else None,
        "actor_role": role,
        "action": action,
        "target_type": target_type,
        "target_id": str(event_inputs["target_id"]),
    }
    with (
        pytest.raises(IntegrityError, match="audit_actor_system_consistent"),
        transaction.atomic(),
    ):
        if method == "create":
            AuditEvent.objects.create(**values)
        elif method == "bulk_create":
            AuditEvent.objects.bulk_create([AuditEvent(**values)])
        else:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO audit_auditevent "
                    "(actor_id, actor_role, action, target_type, target_id, metadata, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, '{}'::jsonb, CURRENT_TIMESTAMP)",
                    [
                        values["actor"].pk if has_actor else None,
                        role,
                        action,
                        target_type,
                        values["target_id"],
                    ],
                )
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize(
    "language,message",
    [
        ("en", "Unsupported eligibility audit metadata."),
        ("fr", "Métadonnées d’audit d’admissibilité non prises en charge."),
    ],
)
def test_eligibility_metadata_error_is_translated(
    eligibility_inputs, language, message
):
    eligibility_inputs["metadata"]["outcome"] = "approved"
    with translation.override(language), pytest.raises(ValidationError) as error:
        services.record(**eligibility_inputs)
    assert error.value.message_dict == {"metadata": [message]}
