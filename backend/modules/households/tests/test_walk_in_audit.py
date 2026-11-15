# AI contribution: 50% or more AI-generated
"""SEC-08/SEC-09: durable, transactional, personal-data-free walk-in audits."""

from copy import deepcopy
from uuid import uuid4

import pytest
from django.apps import apps
from django.db import OperationalError, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from adapters.file_store.memory import InMemoryFileStore
from modules.accounts.tests.factories import UserFactory
from modules.audit.queries import search_events
from modules.households.api.serializers import WalkInDraftReadSerializer
from modules.households.models import Household, HouseholdDraftEvent, Member
from modules.households.services import create_walk_in, submit_walk_in, update_draft
from modules.households.tests.factories import HouseholdFactory, WalkInPayloadFactory
from modules.households.tests.notices.helpers import filed_notice, publish_notice_rule
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish

pytestmark = pytest.mark.django_db
# FIX-29: each read shows the file (the notices and summary show income).
READS = {
    "view": "staff-households-detail",
    "notices": "staff-households-notices",
    "summary": "staff-households-decision-summary",
}
READ_ROUTES = list(READS.values())
OPERATIONS = ["create", "update", "submit", "record_notice", *READS]
EXPECTED_ACTION = {"notices": "view", "summary": "view", "record_notice": "update"}


def notice_rows():
    return list(apps.get_model("documents.IncomeNotice").objects.values())


@pytest.fixture(autouse=True)
def _walk_in_rules():
    """The notice limits and accepted tax years the notices and summary read."""
    publish_notice_rule()
    rule = deepcopy(DEFAULT_RULE_VALUES["auto_approval"])
    publish("auto_approval", rule, UserFactory(role="admin"))


@pytest.fixture
def data():
    return WalkInPayloadFactory()


def client_for(actor):
    client = APIClient()
    client.force_authenticate(actor)
    return client


def perform(client, operation, household, data):
    if operation == "create":
        return client.post(reverse("staff-households-create"), data, format="json")
    if operation in READS:
        return client.get(reverse(READS[operation], kwargs={"id": household.pk}))
    if operation == "record_notice":
        holder = household.members.get(relation=Member.Relation.HOLDER)
        url = reverse("staff-households-notices", kwargs={"id": household.pk})
        return client.post(url, filed_notice(holder), format="multipart")
    route = (
        "staff-households-submit"
        if operation == "submit"
        else "staff-households-detail"
    )
    url = reverse(route, kwargs={"id": household.pk})
    if operation == "update":
        return client.patch(url, {"holder": {"phone": "+15145550999"}}, format="json")
    return client.post(url, {}, format="json")


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_each_walk_in_operation_records_only_actor_target_and_action(
    operation, role, submission_worker, ready_household_factory, data
):
    # rule: SEC-08, SEC-09
    submission_worker.role = role
    submission_worker.save()
    household = ready_household_factory()
    response = perform(client_for(submission_worker), operation, household, data)
    expected_status = 201 if operation in ("create", "record_notice") else 200
    assert response.status_code == expected_status, response.data
    target = response.data["id"] if operation == "create" else household.pk
    event = search_events(household=target, actor=submission_worker.pk).get()
    assert event.action == EXPECTED_ACTION.get(operation, operation)
    assert event.actor_role == role
    assert event.target_type == "household"
    # No holder, contact, address, birth date or member data.
    assert event.metadata == {}
    if operation in READS:
        assert response["Cache-Control"] == "private, no-store"


@pytest.mark.parametrize("operation", OPERATIONS)
def test_audit_insert_failure_prevents_success_and_rolls_back_all_changes(
    operation, submission_worker, ready_household_factory, data, monkeypatch
):
    household = ready_household_factory()
    before = list(Household.objects.values())
    members_before = list(Member.objects.values())
    notices_before = notice_rows()
    events_before = search_events().count()

    def fail(*args, **kwargs):
        raise OperationalError("Audit unavailable")

    # Fail the actual event insert after validation, rather than replacing record().
    monkeypatch.setattr("modules.audit.services.AuditEvent.save", fail)
    with pytest.raises(OperationalError, match="Audit unavailable"):
        perform(client_for(submission_worker), operation, household, data)
    assert list(Household.objects.values()) == before
    assert list(Member.objects.values()) == members_before
    assert notice_rows() == notices_before
    assert InMemoryFileStore.references() == []
    assert not HouseholdDraftEvent.objects.exists()
    assert search_events().count() == events_before


@pytest.mark.parametrize("operation", ["create", "update", "submit"])
def test_outer_rollback_removes_the_change_and_its_central_audit(
    operation, submission_worker, ready_household_factory, data
):
    household = ready_household_factory()
    before = list(Household.objects.values())
    events_before = search_events().count()
    with pytest.raises(RuntimeError, match="abort"), transaction.atomic():
        if operation == "create":
            create_walk_in(data, submission_worker)
        elif operation == "update":
            update_draft(
                household.pk, {"holder": {"phone": "+15145550999"}}, submission_worker
            )
        else:
            submit_walk_in(household.pk, submission_worker)
        assert search_events().count() == events_before + 1
        raise RuntimeError("abort")
    assert list(Household.objects.values()) == before
    assert search_events().count() == events_before
    assert not HouseholdDraftEvent.objects.exists()


@pytest.mark.parametrize("operation", ["create", "update", "submit"])
def test_failed_change_leaves_no_central_event(
    operation, submission_worker, ready_household_factory, data, monkeypatch
):
    household = ready_household_factory()
    events_before = search_events().count()

    def fail(*args, **kwargs):
        raise OperationalError("Household unavailable")

    monkeypatch.setattr(Household, "save", fail)
    with pytest.raises(OperationalError, match="Household unavailable"):
        perform(client_for(submission_worker), operation, household, data)
    assert search_events().count() == events_before


def test_failed_detail_serialization_records_no_disclosure(
    submission_worker, ready_household_factory, monkeypatch
):
    household = ready_household_factory()
    events_before = search_events().count()

    def fail(*args, **kwargs):
        raise RuntimeError("Serialization unavailable")

    monkeypatch.setattr(WalkInDraftReadSerializer, "to_representation", fail)
    with pytest.raises(RuntimeError, match="Serialization unavailable"):
        client_for(submission_worker).get(
            reverse("staff-households-detail", kwargs={"id": household.pk})
        )
    assert search_events().count() == events_before


@pytest.mark.parametrize("route", READ_ROUTES)
@pytest.mark.parametrize(
    "kind,expected_status",
    [("unknown", 404), ("anonymized", 404), ("inactive", 403), ("anonymous", 401)],
)
def test_refused_read_records_no_disclosure(
    route, kind, expected_status, submission_worker, ready_household_factory
):
    household = ready_household_factory()
    identifier = uuid4() if kind == "unknown" else household.pk
    if kind == "anonymized":
        household.anonymized_at = timezone.now()
        household.save()
    if kind == "inactive":
        submission_worker.is_active = False
        submission_worker.save()
    client = APIClient() if kind == "anonymous" else client_for(submission_worker)
    before = search_events().count()
    response = client.get(reverse(route, kwargs={"id": identifier}))
    assert response.status_code == expected_status
    assert search_events().count() == before


@pytest.mark.parametrize("route", READ_ROUTES)
def test_head_probe_does_not_record_a_file_disclosure(
    route, submission_worker, ready_household_factory
):
    household = ready_household_factory()
    before = search_events().count()
    response = client_for(submission_worker).head(
        reverse(route, kwargs={"id": household.pk})
    )
    assert response.status_code == 200
    assert not response.content
    assert search_events().count() == before


def test_duplicate_review_submission_also_records_a_central_event(
    submission_worker, ready_household_factory
):
    household = ready_household_factory()
    HouseholdFactory(status=Household.Status.APPROVED)
    response = perform(client_for(submission_worker), "submit", household, {})
    assert response.status_code == 200
    assert response.data["status"] == "review_required"
    event = search_events(household=household.pk).get()
    assert event.action == "submit"
    assert event.actor_id == submission_worker.pk
    assert event.metadata == {}
