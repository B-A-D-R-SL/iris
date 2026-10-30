# AI contribution: 50% or more AI-generated
import json
from typing import Any
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
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


@pytest.mark.parametrize("outcome", ["approved", "rejected", "review_required"])
def test_record_decision(event_inputs, outcome):
    event_inputs.update(action="decision", metadata={"outcome": outcome})
    event = services.record(**event_inputs)
    event.refresh_from_db()
    assert event.action == "decision"
    assert event.metadata == {"outcome": outcome}


@pytest.mark.parametrize("target_id", [1, "external-123"])
def test_record_accepts_other_record_identifiers(event_inputs, target_id):
    event_inputs["target_id"] = target_id
    assert services.record(**event_inputs).target_id == str(target_id)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actor", None),
        ("action", ""),
        ("action", "unsupported"),
        ("target_type", ""),
        ("target_type", "Household Name"),
        ("target_type", "household\n"),
        ("target_type", "x" * 65),
        ("target_id", None),
        ("target_id", True),
        ("target_id", ""),
        ("target_id", "   "),
        ("target_id", "x" * 65),
        ("metadata", None),
        ("metadata", []),
        ("metadata", {"outcome": "personal free text"}),
        ("metadata", {"outcome": {"sin": "000000000"}}),
        ("metadata", {"outcome": ["approved"]}),
    ],
)
def test_record_rejects_invalid_inputs_without_writing(event_inputs, field, value):
    event_inputs[field] = value
    with pytest.raises(ValidationError) as error:
        services.record(**event_inputs)
    assert field in error.value.message_dict
    assert not AuditEvent.objects.exists()


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


def test_record_rejects_unsaved_actor(django_user_model, event_inputs):
    event_inputs["actor"] = django_user_model(email="unsaved@example.test")
    with pytest.raises(ValidationError, match="actor"):
        services.record(**event_inputs)
    assert not AuditEvent.objects.exists()


def test_record_rejects_invalid_actor_role(actor, event_inputs):
    actor.role = "unknown"
    with pytest.raises(ValidationError):
        services.record(**event_inputs)
    assert not AuditEvent.objects.exists()


def test_record_rolls_back_with_callers_transaction(actor, event_inputs):
    with pytest.raises(RuntimeError), transaction.atomic():
        actor.role = "admin"
        actor.save(update_fields=["role"])
        services.record(**event_inputs)
        raise RuntimeError("Caller failed")

    actor.refresh_from_db()
    assert actor.role == "intake_worker"
    assert not AuditEvent.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_record_commits_with_callers_transaction(event_inputs):
    with transaction.atomic():
        event = services.record(**event_inputs)
    assert AuditEvent.objects.filter(pk=event.pk).exists()


@pytest.mark.parametrize(
    "operation", ["save", "update", "bulk_update", "delete", "queryset_delete"]
)
def test_postgresql_rejects_orm_mutations(event_inputs, operation):
    event = services.record(**event_inputs)
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        if operation == "save":
            event.action = "decision"
            event.save()
        elif operation == "update":
            AuditEvent.objects.filter(pk=event.pk).update(action="decision")
        elif operation == "bulk_update":
            event.action = "decision"
            AuditEvent.objects.bulk_update([event], ["action"])
        elif operation == "delete":
            event.delete()
        else:
            AuditEvent.objects.filter(pk=event.pk).delete()

    event.refresh_from_db()
    assert event.action == "view"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE audit_auditevent SET action = 'decision' WHERE id = %s",
        "DELETE FROM audit_auditevent WHERE id = %s",
    ],
)
def test_postgresql_rejects_direct_sql_mutations(event_inputs, sql):
    event = services.record(**event_inputs)
    with (
        pytest.raises(IntegrityError, match="append-only"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(sql, [event.pk])

    event.refresh_from_db()
    assert event.action == "view"


def test_actor_deletion_preserves_event(actor, event_inputs):
    event = services.record(**event_inputs)
    with pytest.raises(ProtectedError):
        actor.delete()
    assert AuditEvent.objects.filter(pk=event.pk).exists()


@pytest.mark.parametrize("target_type", ["household", "partner_application"])
def test_target_type_validation(target_type):
    field = AuditEvent._meta.get_field("target_type")
    assert field.clean(target_type, None) == target_type


@pytest.mark.parametrize("target_type", ["Household", "household\n", "household name"])
def test_target_type_validation_rejects_free_text(target_type):
    field = AuditEvent._meta.get_field("target_type")
    with pytest.raises(ValidationError):
        field.clean(target_type, None)


def test_record_rejects_deleted_actor(actor, event_inputs):
    actor_id = actor.pk
    actor.delete()
    actor.pk = actor_id

    with pytest.raises(ValidationError, match="actor"):
        services.record(**event_inputs)
    assert not AuditEvent.objects.exists()


def test_record_propagates_database_failure(event_inputs, monkeypatch):
    def fail_save(self):
        raise OperationalError("Database unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(AuditEvent, "save", fail_save)
        with pytest.raises(OperationalError, match="Database unavailable"):
            services.record(**event_inputs)

    assert not AuditEvent.objects.exists()
    assert services.record(**event_inputs).pk is not None


@pytest.mark.django_db(transaction=True)
def test_append_only_migration_is_reversible(event_inputs):
    event = services.record(**event_inputs)
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([("audit", "0001_initial")])
        assert AuditEvent.objects.filter(pk=event.pk).update(action="decision") == 1
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    event.refresh_from_db()
    assert event.action == "decision"
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        AuditEvent.objects.filter(pk=event.pk).delete()
