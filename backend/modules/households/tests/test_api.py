# AI contribution: 50% or more AI-generated

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
    ("intake_worker", "self"),
    ("intake_worker", "intake_worker"),
    ("intake_worker", "admin"),
    ("intake_worker", None),
    ("admin", "self"),
    ("admin", "intake_worker"),
    ("admin", "admin"),
    ("admin", None),
]


@pytest.fixture
def access_file(request, ready_household_factory):
    role, owner = request.param
    actor = UserFactory(role=role)
    creator = None
    if owner == "self":
        creator = actor
    elif owner:
        creator = UserFactory(role=owner)
    household = ready_household_factory(created_by=creator)
    return household, actor


@pytest.fixture
def access_client(access_file):
    household, actor = access_file
    client = APIClient()
    client.force_authenticate(user=actor)
    return household, actor, client


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


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_can_read_shared_walk_in(access_client):
    household, _, client = access_client
    before = household.updated_at
    response = _request(client, "read", household.pk)
    assert response.status_code == 200, response.data
    assert response.data["id"] == str(household.pk)
    _assert_unchanged(household, before)


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_can_edit_shared_walk_in(access_client):
    household, actor, client = access_client
    response = _request(client, "edit", household.pk)
    assert response.status_code == 200, response.data
    household.refresh_from_db()
    assert household.phone == "+15145550999"
    assert household.draft_events.get().actor_id == actor.pk


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_can_submit_shared_walk_in(access_client):
    household, actor, client = access_client
    response = _request(client, "submit", household.pk)
    assert response.status_code == 200, response.data
    household.refresh_from_db()
    assert household.status == Household.Status.SUBMITTED
    assert household.draft_events.get().actor_id == actor.pk


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_query_reads_shared_walk_in(access_file):
    household, actor = access_file
    assert walk_in_for_staff(household.pk, actor) == household


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_can_search_and_resume_shared_walk_in(access_file):
    household, actor = access_file
    assert list(search_for_staff("Exemple", actor)) == [household]
    assert can_resume_walk_in(household, actor) is True


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_service_edits_shared_walk_in(access_file):
    household, actor = access_file
    update_draft(household.pk, {"holder": {"phone": "+15145550999"}}, actor)
    household.refresh_from_db()
    assert household.phone == "+15145550999"
    assert household.draft_events.get().actor_id == actor.pk


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_service_submits_shared_walk_in(access_file):
    household, actor = access_file
    submit_walk_in(household.pk, actor)
    household.refresh_from_db()
    assert household.status == Household.Status.SUBMITTED
    assert household.draft_events.get().actor_id == actor.pk


# rule: BR-HH-ACCESS-001
@pytest.mark.parametrize("access_file", ACCESS_CASES, indirect=True)
def test_staff_can_check_duplicates_for_shared_walk_in(access_file):
    household, actor = access_file
    before = household.updated_at
    with locked_duplicate_check(household.pk, actor) as (checked, matched):
        assert checked.pk == household.pk
        assert matched is False
    _assert_unchanged(household, before)
