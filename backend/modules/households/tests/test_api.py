# AI contribution: 50% or more AI-generated

import uuid
from contextlib import nullcontext

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.audit.queries import search_events
from modules.households.models import Household
from modules.households.policies import can_resume_walk_in
from modules.households.queries import search_for_staff, walk_in_for_staff
from modules.households.services import (
    locked_duplicate_check,
    submit_walk_in,
    update_draft,
)
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

ACCESS_CASES = [
    ("intake_worker", "self", True),
    ("intake_worker", "intake_worker", False),
    ("intake_worker", "admin", False),
    ("intake_worker", None, False),
    ("admin", "self", True),
    ("admin", "intake_worker", True),
    ("admin", "admin", True),
    ("admin", None, True),
]


@pytest.fixture
def access_file(request, ready_household_factory):
    role, owner, allowed = request.param
    actor = UserFactory(role=role)
    creator = None
    if owner == "self":
        creator = actor
    elif owner:
        creator = UserFactory(role=owner)
    household = ready_household_factory(created_by=creator)
    return household, actor, allowed


@pytest.fixture
def access_client(access_file):
    household, actor, allowed = access_file
    client = APIClient()
    client.force_authenticate(user=actor)
    return household, actor, allowed, client


def _request(client, action, household_id):
    if action == "create":
        return client.post(reverse("staff-households-create"), {}, format="json")
    if action == "search":
        return client.get(reverse("staff-households-create"), {"q": "Example"})
    route = (
        "staff-households-submit" if action == "submit" else "staff-households-detail"
    )
    url = reverse(route, kwargs={"id": household_id})
    if action == "read":
        return client.get(url)
    if action == "edit":
        return client.patch(url, {"holder": {"phone": "+15145550999"}}, format="json")
    return client.post(url, {}, format="json")


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
@pytest.mark.parametrize("action", ["create", "read", "edit", "submit", "search"])
def test_nonstaff_cannot_manage_even_their_own_file(
    role, action, ready_household_factory
):
    store = StoreFactory() if role.startswith("store_") else None
    actor = UserFactory(role=role, store=store)
    household = ready_household_factory(created_by=actor)
    client = APIClient()
    client.force_login(actor)
    response = _request(client, action, household.pk)
    assert response.status_code == 403
    household.refresh_from_db()
    assert Household.objects.count() == 1
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None
    assert not household.draft_events.exists()
    assert not search_events(actor=actor.pk).exists()


def _assert_unchanged(household, updated_at):
    household.refresh_from_db()
    assert household.updated_at == updated_at
    assert household.status == Household.Status.DRAFT
    assert household.phone == "+15145550101"
    assert household.submitted_at is None
    assert not household.draft_events.exists()


def _checked_request(client, action, household, allowed):
    before = household.updated_at
    response = _request(client, action, household.pk)
    assert response.status_code == (200 if allowed else 404), response.data
    household.refresh_from_db()
    if not allowed:
        assert response.data["fields"] == {}
        _assert_unchanged(household, before)
        missing = _request(client, action, uuid.uuid4())
        assert response.data == missing.data
    return response


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_walk_in_api_read_enforces_creator_access(access_client):
    household, _, allowed, client = access_client
    response = _checked_request(client, "read", household, allowed)
    if allowed:
        assert response.data["id"] == str(household.pk)


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_walk_in_api_edit_enforces_creator_access(access_client):
    household, actor, allowed, client = access_client
    _checked_request(client, "edit", household, allowed)
    if allowed:
        assert household.phone == "+15145550999"
        assert household.draft_events.get().actor_id == actor.pk


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_walk_in_api_submit_enforces_creator_access(access_client):
    household, actor, allowed, client = access_client
    _checked_request(client, "submit", household, allowed)
    if allowed:
        assert household.status == Household.Status.SUBMITTED
        assert household.draft_events.get().actor_id == actor.pk


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_walk_in_query_enforces_creator_access(access_file):
    household, actor, allowed = access_file
    assert walk_in_for_staff(household.pk, actor) == (household if allowed else None)


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_search_query_enforces_creator_access(access_file):
    household, actor, allowed = access_file
    assert list(search_for_staff("Exemple", actor)) == ([household] if allowed else [])
    assert can_resume_walk_in(household, actor) is allowed


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_draft_edit_service_enforces_creator_access(access_file):
    household, actor, allowed = access_file
    before = household.updated_at
    with nullcontext() if allowed else pytest.raises(Household.DoesNotExist):
        update_draft(household.pk, {"holder": {"phone": "+15145550999"}}, actor)
    if allowed:
        household.refresh_from_db()
        assert household.phone == "+15145550999"
        assert household.draft_events.get().actor_id == actor.pk
    else:
        _assert_unchanged(household, before)


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_submission_service_enforces_creator_access(access_file):
    household, actor, allowed = access_file
    before = household.updated_at
    with nullcontext() if allowed else pytest.raises(Household.DoesNotExist):
        submit_walk_in(household.pk, actor)
    if allowed:
        household.refresh_from_db()
        assert household.status == Household.Status.SUBMITTED
        assert household.draft_events.get().actor_id == actor.pk
    else:
        _assert_unchanged(household, before)


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_locked_duplicate_check_enforces_creator_access(access_file):
    household, actor, allowed = access_file
    before = household.updated_at
    with (
        nullcontext() if allowed else pytest.raises(Household.DoesNotExist),
        locked_duplicate_check(household.pk, actor) as (checked, matched),
    ):
        assert checked.pk == household.pk
        assert matched is False
    _assert_unchanged(household, before)


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("action", ["edit", "submit"])
@pytest.mark.parametrize("payload", [{}, {"status": "approved"}, []])
def test_other_workers_file_is_hidden_before_input_validation(
    action, payload, ready_household_factory
):
    household = ready_household_factory()
    client = APIClient()
    client.force_authenticate(user=UserFactory(role="intake_worker"))
    route = "staff-households-detail" if action == "edit" else "staff-households-submit"
    url = reverse(route, kwargs={"id": household.pk})
    send = client.patch if action == "edit" else client.post
    response = send(url, payload, format="json")
    assert response.status_code == 404
    assert response.data["fields"] == {}
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert not household.draft_events.exists()
