# AI contribution: 50% or more AI-generated

import uuid
from contextlib import nullcontext

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.policies import can_resume_walk_in
from modules.households.queries import search_for_staff, walk_in_for_staff
from modules.households.services import (
    locked_duplicate_check,
    submit_walk_in,
    update_draft,
)

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


def _request(client, action, household_id):
    route = (
        "staff-households-submit" if action == "submit" else "staff-households-detail"
    )
    url = reverse(route, kwargs={"id": household_id})
    if action == "read":
        return client.get(url)
    if action == "edit":
        return client.patch(url, {"holder": {"phone": "+15145550999"}}, format="json")
    return client.post(url, {}, format="json")


@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
@pytest.mark.parametrize("action", ["read", "edit", "submit"])
def test_walk_in_api_enforces_creator_access(access_file, action):
    household, actor, allowed = access_file
    client = APIClient()
    client.force_authenticate(user=actor)
    before = household.updated_at
    response = _request(client, action, household.pk)
    assert response.status_code == (200 if allowed else 404), response.data
    household.refresh_from_db()
    if allowed:
        if action == "read":
            assert response.data["id"] == str(household.pk)
        elif action == "edit":
            assert household.phone == "+15145550999"
            assert household.draft_events.get().actor_id == actor.pk
        else:
            assert household.status == Household.Status.SUBMITTED
            assert household.draft_events.get().actor_id == actor.pk
    else:
        assert response.data["fields"] == {}
        assert household.updated_at == before
        assert household.status == Household.Status.DRAFT
        assert household.phone == "+15145550101"
        assert household.submitted_at is None
        assert not household.draft_events.exists()
        missing = _request(client, action, uuid.uuid4())
        assert response.data == missing.data


@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
@pytest.mark.parametrize("action", ["read", "search", "edit", "submit", "locked_check"])
def test_queries_and_services_enforce_creator_access(access_file, action):
    household, actor, allowed = access_file
    if action == "read":
        assert walk_in_for_staff(household.pk, actor) == (
            household if allowed else None
        )
        return
    if action == "search":
        assert list(search_for_staff("Exemple", actor)) == (
            [household] if allowed else []
        )
        assert can_resume_walk_in(household, actor) is allowed
        return
    before = household.updated_at
    with nullcontext() if allowed else pytest.raises(Household.DoesNotExist):
        if action == "edit":
            update_draft(household.pk, {"holder": {"phone": "+15145550999"}}, actor)
        elif action == "submit":
            submit_walk_in(household.pk, actor)
        else:
            with locked_duplicate_check(household.pk, actor) as (checked, matched):
                assert checked.pk == household.pk
                assert matched is False
    household.refresh_from_db()
    if not allowed:
        assert household.updated_at == before
        assert household.status == Household.Status.DRAFT
        assert household.submitted_at is None
        assert not household.draft_events.exists()


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
