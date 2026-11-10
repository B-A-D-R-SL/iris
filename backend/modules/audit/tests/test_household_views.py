# AI contribution: 50% or more AI-generated
"""Search pages preserve one validated, append-only event per returned file."""

from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from modules.audit.models import AuditEvent
from modules.audit.services import record_household_views


@pytest.fixture
def actor(db, django_user_model):
    return django_user_model.objects.create_user(
        "search-worker@example.test", role="intake_worker"
    )


def test_page_views_use_one_insert_and_preserve_each_identifier(
    actor, django_assert_num_queries
):
    """Record every disclosed file using one insert with no personal metadata."""
    # rule: BR-HH-AUDIT-001
    identifiers = [uuid4(), uuid4(), uuid4()]
    with django_assert_num_queries(1):
        events = record_household_views(actor, identifiers)
    assert len(events) == 3
    assert set(AuditEvent.objects.values_list("target_id", flat=True)) == {
        str(identifier) for identifier in identifiers
    }
    for event in events:
        assert event.actor_id == actor.pk
        assert event.actor_role == "intake_worker"
        assert event.action == "view" and event.target_type == "household"
        assert event.metadata == {}


@pytest.mark.parametrize("invalid", ["private-search-text", None, True, 1])
def test_invalid_identifier_never_partially_records_a_page(actor, invalid):
    with pytest.raises(ValidationError, match="household UUID"):
        record_household_views(actor, [uuid4(), invalid])
    assert AuditEvent.objects.count() == 0


def test_unsaved_actor_is_rejected(actor, django_user_model):
    unsaved = django_user_model(email="unsaved@example.test", role="intake_worker")
    with pytest.raises(ValidationError, match="saved user"):
        record_household_views(unsaved, [uuid4()])
    assert AuditEvent.objects.count() == 0


def test_actor_role_is_validated(actor):
    actor.role = "unsupported"
    with pytest.raises(ValidationError):
        record_household_views(actor, [uuid4()])
    assert AuditEvent.objects.count() == 0


def test_page_views_join_the_callers_transaction(actor):
    with pytest.raises(RuntimeError, match="roll back"), transaction.atomic():
        record_household_views(actor, [uuid4()])
        raise RuntimeError("roll back")
    assert AuditEvent.objects.count() == 0


def test_empty_search_results_need_no_insert(actor, django_assert_num_queries):
    with django_assert_num_queries(0):
        assert record_household_views(actor, []) == []
