# AI contribution: 50% or more AI-generated

import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


def client_for(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def submit_url(household):
    return reverse("staff-households-submit", kwargs={"id": household.pk})


# rule: BR-DUP-001, BR-DUP-002
@pytest.mark.parametrize("role", ["intake_worker", "admin"])
@pytest.mark.parametrize("duplicate", [True, False])
def test_creator_or_admin_can_submit_and_see_the_persisted_outcome(
    role, duplicate, ready_household_factory
):
    actor = UserFactory(role=role)
    household = ready_household_factory(
        **({"created_by": actor} if role == "intake_worker" else {})
    )
    if duplicate:
        HouseholdFactory(status=Household.Status.APPROVED)
    response = client_for(actor).post(submit_url(household), {}, format="json")
    assert response.status_code == 200, response.data
    household.refresh_from_db()
    expected = (
        Household.Status.REVIEW_REQUIRED if duplicate else Household.Status.SUBMITTED
    )
    assert response.data["status"] == household.status == expected
    assert (
        response.data["status_reason"]
        == household.status_reason
        == ("POSSIBLE_DUPLICATE" if duplicate else "")
    )
    assert response.data["submitted_at"] and household.submitted_at is not None
    assert set(response.data) == {"id", "status", "status_reason", "submitted_at"}


def test_main_path_creates_draft_and_submits_through_api_and_database(
    submission_worker,
):
    client = client_for(submission_worker)
    data = {
        "holder": {
            "first_name": "Example",
            "last_name": "Holder",
            "date_of_birth": "1990-01-01",
            "phone": "+15145550101",
        },
        "address": {
            "street_number": "100",
            "street_name": "rue Exemple",
            "unit": "4",
            "city": "Montréal",
            "postal_code": "H2X 1Y4",
        },
        "identity_checked_in_person": True,
        "consent_data_processing": True,
    }
    created = client.post(reverse("staff-households-create"), data, format="json")
    assert created.status_code == 201, created.data
    existing = HouseholdFactory(unit="4", status=Household.Status.APPROVED)
    household = Household.objects.get(pk=created.data["id"])
    response = client.post(submit_url(household), {}, format="json")
    assert response.status_code == 200, response.data
    household.refresh_from_db()
    assert (
        household.status == response.data["status"] == Household.Status.REVIEW_REQUIRED
    )
    assert (
        household.status_reason
        == response.data["status_reason"]
        == "POSSIBLE_DUPLICATE"
    )
    existing.refresh_from_db()
    assert existing.status == Household.Status.APPROVED
    assert Household.objects.count() == 2


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_nonstaff_cannot_submit_even_if_they_created_the_file(
    role, ready_household_factory
):
    values = {"store": StoreFactory()} if role.startswith("store_") else {}
    user = UserFactory(role=role, **values)
    household = ready_household_factory(created_by=user)
    response = client_for(user).post(submit_url(household), {}, format="json")
    assert response.status_code == 403
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert household.submitted_at is None


def test_signed_out_request_is_refused(ready_household_factory):
    household = ready_household_factory()
    response = client_for().post(submit_url(household), {}, format="json")
    assert response.status_code == 401
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_inactive_staff_cannot_submit(role, ready_household_factory):
    household = ready_household_factory()
    response = client_for(UserFactory(role=role, is_active=False)).post(
        submit_url(household), {}, format="json"
    )
    assert response.status_code == 403
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


@pytest.mark.parametrize(
    "payload",
    [{"status": "approved"}, {"status_reason": ""}, {"address_key": "fake"}, []],
)
def test_submission_refuses_client_supplied_fields(
    payload, ready_household_factory, submission_worker
):
    household = ready_household_factory()
    response = client_for(submission_worker).post(
        submit_url(household), payload, format="json"
    )
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


@pytest.mark.parametrize("online", [False, True])
def test_missing_or_online_households_are_not_exposed(submission_worker, online):
    household_id = (
        HouseholdFactory(channel=Household.Channel.ONLINE).pk
        if online
        else uuid.uuid4()
    )
    response = client_for(submission_worker).post(
        reverse("staff-households-submit", kwargs={"id": household_id}),
        {},
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("language", "message"),
    [
        ("en", "Complete the address before submission."),
        ("fr", "Complétez l'adresse avant de soumettre le dossier."),
    ],
)
def test_incomplete_draft_has_a_translated_field_error(
    language, message, ready_household_factory, submission_worker
):
    household = ready_household_factory(street_number="")
    response = client_for(submission_worker).post(
        submit_url(household), {}, format="json", HTTP_ACCEPT_LANGUAGE=language
    )
    assert response.status_code == 400
    assert response.data["fields"] == {"address": [message]}
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT


def test_repeat_submission_does_not_clear_duplicate_review(
    ready_household_factory, submission_worker
):
    household = ready_household_factory()
    HouseholdFactory(status=Household.Status.APPROVED)
    client = client_for(submission_worker)
    assert client.post(submit_url(household), {}, format="json").status_code == 200
    household.refresh_from_db()
    submitted_at = household.submitted_at
    response = client.post(submit_url(household), {}, format="json")
    assert response.status_code == 400
    household.refresh_from_db()
    assert household.status == Household.Status.REVIEW_REQUIRED
    assert household.status_reason == "POSSIBLE_DUPLICATE"
    assert household.submitted_at == submitted_at
