# AI contribution: 50% or more AI-generated
"""Check submission history and logs against real transaction outcomes."""

import json
import logging
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from iris.observability import JsonLogFormatter
from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household, HouseholdDraftEvent
from modules.households.services import submit_walk_in
from modules.households.tests.factories import HouseholdFactory

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("duplicate", [False, True])
@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_submission_records_actor_and_role_for_both_outcomes(
    duplicate, role, ready_household_factory
):
    """A review result is still a submission by the acting staff member."""
    actor = UserFactory(role=role)
    household = ready_household_factory(
        **({"created_by": actor} if role == "intake_worker" else {})
    )
    if duplicate:
        HouseholdFactory(status=Household.Status.APPROVED)
    before = timezone.now()
    submit_walk_in(household.pk, actor)
    event = household.draft_events.get(action=HouseholdDraftEvent.Action.SUBMITTED)
    assert event.household_id == household.pk
    assert event.actor_id == actor.pk
    assert event.actor_role == role
    assert before <= event.created_at <= timezone.now()
    assert timezone.is_aware(event.created_at)
    actor.role = "admin" if role == "intake_worker" else "intake_worker"
    actor.save()
    event.refresh_from_db()
    assert event.actor_role == role


@pytest.mark.parametrize(
    ("duplicate", "expected"),
    [(False, "household_submitted"), (True, "household_duplicate_review")],
)
def test_success_log_waits_for_outer_commit_and_contains_no_personal_data(
    duplicate, expected, ready_household_factory, submission_worker, caplog
):
    household = ready_household_factory()
    if duplicate:
        HouseholdFactory(status=Household.Status.APPROVED)
    with caplog.at_level(logging.INFO, logger="iris.households"):
        with transaction.atomic():
            submit_walk_in(household.pk, submission_worker)
            assert not caplog.records
        assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.name == "iris.households"
    assert record.event == record.getMessage() == expected
    assert record.args == ()
    standard_fields = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
    assert set(record.__dict__) - standard_fields == {"event"}
    payload = json.loads(JsonLogFormatter().format(record))
    assert set(payload) == {"timestamp", "level", "logger", "event"}
    assert payload["level"] == "INFO" and payload["event"] == expected


@pytest.mark.parametrize("duplicate", [False, True])
def test_outer_rollback_removes_submission_event_and_success_log(
    duplicate, ready_household_factory, submission_worker, caplog
):
    household = ready_household_factory()
    if duplicate:
        HouseholdFactory(status=Household.Status.APPROVED)
    with (
        caplog.at_level(logging.INFO, logger="iris.households"),
        pytest.raises(RuntimeError, match="abort"),
        transaction.atomic(),
    ):
        submit_walk_in(household.pk, submission_worker)
        assert household.draft_events.filter(action="submitted").count() == 1
        assert not caplog.records
        raise RuntimeError("abort")
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None
    assert not household.draft_events.filter(action="submitted").exists()
    assert not caplog.records


def test_validation_failure_leaves_no_submission_event_or_log(
    ready_household_factory, submission_worker, caplog
):
    household = ready_household_factory(consent_text_version="")
    with (
        caplog.at_level(logging.INFO, logger="iris.households"),
        pytest.raises(ValidationError),
    ):
        submit_walk_in(household.pk, submission_worker)
    assert not household.draft_events.filter(action="submitted").exists()
    assert not caplog.records


def test_audit_failure_rolls_back_the_submission(
    ready_household_factory, submission_worker, caplog
):
    """Saving the household alone must not count as a successful submission."""
    household = ready_household_factory()
    with (
        patch(
            "modules.households.services.HouseholdDraftEvent.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ),
        caplog.at_level(logging.INFO, logger="iris.households"),
        pytest.raises(RuntimeError, match="audit unavailable"),
    ):
        submit_walk_in(household.pk, submission_worker)
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None
    assert not household.draft_events.filter(action="submitted").exists()
    assert not caplog.records
