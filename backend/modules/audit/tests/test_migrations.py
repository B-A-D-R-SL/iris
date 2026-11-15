# AI contribution: 50% or more AI-generated
import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from modules.audit import services
from modules.audit.models import AuditEvent


@pytest.mark.django_db(transaction=True)
def test_actor_constraint_commits_before_validating_history(event_inputs):
    event = services.record(**event_inputs)
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    observed = []

    def inspect_validation(execute, sql, params, many, context):
        if "VALIDATE CONSTRAINT audit_actor_system_consistent" in sql:
            assert connection.get_autocommit()
            assert not connection.in_atomic_block
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT convalidated FROM pg_constraint WHERE "
                    "conrelid = 'audit_auditevent'::regclass "
                    "AND conname = 'audit_actor_system_consistent'"
                )
                observed.append(cursor.fetchone()[0])
        return execute(sql, params, many, context)

    try:
        executor.migrate([("audit", "0006_household_events_and_system_actor")])
        with connection.execute_wrapper(inspect_validation):
            MigrationExecutor(connection).migrate(latest)
        assert observed == [False]
        assert AuditEvent.objects.filter(pk=event.pk).exists()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT convalidated FROM pg_constraint WHERE "
                "conrelid = 'audit_auditevent'::regclass "
                "AND conname = 'audit_actor_system_consistent'"
            )
            assert cursor.fetchone()[0] is True
    finally:
        MigrationExecutor(connection).migrate(latest)


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


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("system_event", [False, True])
def test_household_event_migration_preserves_history_and_append_only_protection(
    event_inputs,
    system_inputs,
    system_event,
):
    if system_event:
        event_inputs = system_inputs
    event = services.record(**event_inputs)
    original = AuditEvent.objects.values().get(pk=event.pk)
    executor = MigrationExecutor(connection)
    previous = [("audit", "0005_merge_publication_and_suspension_actions")]
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate(previous)
        old = executor.loader.project_state(previous).apps.get_model(
            "audit", "AuditEvent"
        )
        assert not old._meta.get_field("actor").null
        assert old.objects.values().get(pk=event.pk) == original
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(
                cursor, "audit_auditevent"
            )
        assert next(column for column in columns if column.name == "actor_id").null_ok
        # Rolling back model state must not remove database history protection.
        with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
            old.objects.filter(pk=event.pk).update(actor_role="admin")
        with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
            old.objects.filter(pk=event.pk).delete()
    finally:
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
    event.refresh_from_db()
    assert AuditEvent.objects.values().get(pk=event.pk) == original
    assert AuditEvent._meta.get_field("actor").null
    with pytest.raises(IntegrityError, match="append-only"), transaction.atomic():
        AuditEvent.objects.filter(pk=event.pk).delete()
