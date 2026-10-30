# AI contribution: 50% or more AI-generated
import json
from typing import Any
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from modules.audit import services
from modules.audit.models import AuditEvent


@pytest.fixture
def actor(db, django_user_model):
    return django_user_model.objects.create_user(
        "generated@example.test", role="intake_worker", first_name="Example"
    )


@pytest.fixture
def event_inputs(actor) -> dict[str, Any]:
    return {
        "actor": actor,
        "action": "view",
        "target_type": "household",
        "target_id": uuid4(),
        "metadata": {},
    }


def test_public_record_persists_event_in_postgresql(event_inputs):
    assert connection.vendor == "postgresql"
    before = timezone.now()
    event = services.record(**event_inputs)
    after = timezone.now()
    saved = AuditEvent.objects.get(pk=event.pk)

    assert saved.actor == event_inputs["actor"]
    assert saved.actor_role == "intake_worker"
    assert saved.action == "view"
    assert saved.target_type == "household"
    assert saved.target_id == str(event_inputs["target_id"])
    assert before <= saved.created_at <= after
    assert timezone.is_aware(saved.created_at)
    assert saved.metadata == {}
    row = AuditEvent.objects.values().get(pk=event.pk)
    assert set(row) == {
        "id",
        "actor_id",
        "actor_role",
        "action",
        "target_type",
        "target_id",
        "metadata",
        "created_at",
    }
    payload = json.dumps(row, default=str)
    assert "generated@example.test" not in payload
    assert "Example" not in payload


@pytest.mark.parametrize(
    "role", ["beneficiary", "store_staff", "store_manager", "intake_worker", "admin"]
)
def test_record_snapshots_each_role(actor, event_inputs, role):
    actor.role = role
    actor.save(update_fields=["role"])
    event = services.record(**event_inputs)

    actor.role = "admin" if role != "admin" else "beneficiary"
    actor.save(update_fields=["role"])
    event.refresh_from_db()

    assert event.actor_role == role
    assert event.actor.role == actor.role


@pytest.mark.parametrize(
    "key",
    [
        "name",
        "email",
        "phone",
        "address",
        "sin",
        "income",
        "immigration_status",
        "document_text",
    ],
)
def test_record_rejects_personal_metadata(event_inputs, key):
    event_inputs["metadata"] = {key: "sensitive value"}
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**event_inputs)
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize("target_type", ["household", "partner_application"])
def test_target_type_validation(target_type):
    field = AuditEvent._meta.get_field("target_type")
    assert field.clean(target_type, None) == target_type


@pytest.mark.parametrize("target_type", ["Household", "household\n", "household name"])
def test_target_type_validation_rejects_free_text(target_type):
    field = AuditEvent._meta.get_field("target_type")
    with pytest.raises(ValidationError):
        field.clean(target_type, None)
