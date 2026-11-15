# AI contribution: 50% or more AI-generated
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.urls import reverse

from modules.audit import services
from modules.audit.models import AuditEvent


@pytest.mark.parametrize(
    "field,value",
    [
        ("decision_id", "synthetic@example.test"),
        ("decision_id", ""),
        ("decision_id", None),
        ("decision_id", 123),
        ("decision_id", {}),
        ("outcome", "approved"),
        ("outcome", "private free text"),
        ("outcome", {}),
        ("outcome", []),
        ("rule_version", True),
        ("rule_version", "2"),
        ("rule_version", 0),
        ("rule_version", -1),
        ("rule_version", None),
    ],
)
def test_eligibility_metadata_rejects_wrong_types_and_unbounded_values(
    eligibility_inputs, field, value
):
    eligibility_inputs["metadata"][field] = value
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**eligibility_inputs)
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize(
    "key",
    [
        "name",
        "email",
        "phone",
        "address",
        "date_of_birth",
        "sin",
        "adult_incomes_cents",
        "threshold_cents",
        "document_text",
    ],
)
def test_eligibility_metadata_rejects_every_extra_personal_field(
    eligibility_inputs, key
):
    eligibility_inputs["metadata"][key] = "private value"
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**eligibility_inputs)
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize("key", ["decision_id", "outcome", "rule_version"])
def test_eligibility_metadata_requires_all_references(eligibility_inputs, key):
    del eligibility_inputs["metadata"][key]
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**eligibility_inputs)
    assert not AuditEvent.objects.exists()


def test_eligibility_audit_requires_a_household_target(eligibility_inputs):
    eligibility_inputs["target_type"] = "external_record"
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**eligibility_inputs)
    assert not AuditEvent.objects.exists()


def test_system_decision_is_returned_by_admin_search(system_inputs, client, actor):
    actor.role = "admin"
    actor.save()
    system_inputs["actor"] = None
    event = services.record(**system_inputs)
    client.force_login(actor)
    response = client.get(reverse("audit-search"), {"household": event.target_id})
    assert response.status_code == 200
    item = response.json()["results"][0]
    assert item["actor"] is None
    assert item["actor_role"] == "system"
    assert item["metadata"] == system_inputs["metadata"]


@pytest.mark.parametrize("action", ["view", "create", "update", "submit"])
@pytest.mark.parametrize(
    "metadata", [{"outcome": "eligible"}, {"email": "private@example.test"}]
)
def test_household_operations_reject_all_metadata(event_inputs, action, metadata):
    event_inputs.update(action=action, metadata=metadata)
    with pytest.raises(ValidationError, match="metadata"):
        services.record(**event_inputs)
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE audit_auditevent SET actor_role = 'admin' WHERE id = %s",
        "DELETE FROM audit_auditevent WHERE id = %s",
    ],
)
def test_system_audit_rows_remain_append_only(system_inputs, sql):
    system_inputs["actor"] = None
    event = services.record(**system_inputs)
    with (
        pytest.raises(IntegrityError, match="append-only"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(sql, [event.pk])
    event.refresh_from_db()
    assert event.actor_id is None
    assert event.actor_role == "system"
