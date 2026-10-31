# AI contribution: 50% or more AI-generated
"""Database and API coverage for T-03.17.2 and T-03.17.3."""

from copy import deepcopy
from datetime import date

import pytest
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household, HouseholdDraftEvent, Member
from modules.households.services import create_walk_in, update_draft
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def data():
    return {
        "holder": {
            "first_name": "Example",
            "last_name": "Holder",
            "date_of_birth": "1998-05-15",
            "phone": "(514) 555-0123",
            "preferred_language": "en",
            "email": "EXAMPLE@EXAMPLE.TEST",
        },
        "address": {
            "street_number": "123",
            "street_name": "rue Émile",
            "unit": "4",
            "city": "Montréal",
            "postal_code": "h2x1y4",
        },
        "members": [
            {
                "first_name": "Example",
                "last_name": "Child",
                "date_of_birth": "2017-01-03",
                "relation": "child",
            }
        ],
        "identity_checked_in_person": True,
    }


@pytest.fixture
def worker():
    return UserFactory(role="intake_worker")


def _client(user):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_allowed_staff_create_read_and_patch(role, data):
    user = UserFactory(role=role)
    client = _client(user)
    create = client.post(reverse("staff-households-create"), data, format="json")
    assert create.status_code == 201, create.data
    household = Household.objects.get(pk=create.data["id"])
    assert household.created_by == user
    assert household.channel == Household.Channel.WALK_IN
    assert household.status == Household.Status.DRAFT
    assert household.phone == "+15145550123"
    assert household.email == "example@example.test"
    assert household.address_key == "123|R EMILE|4|H2X1Y4"
    assert household.postal_code == "H2X 1Y4"
    assert household.identity_checked_in_person
    assert household.verified_by == user and household.verified_at
    assert household.members.count() == 2
    assert household.members.get(relation=Member.Relation.HOLDER).date_of_birth == date(
        1998, 5, 15
    )
    assert create.data["created_by_email"] == user.email

    url = reverse("staff-households-detail", kwargs={"id": household.pk})
    assert client.get(url).status_code == 200
    update = client.patch(
        url, {"address": {"street_name": "avenue Émile"}}, format="json"
    )
    assert update.status_code == 200, update.data
    household.refresh_from_db()
    assert household.address_key == "123|AV EMILE|4|H2X1Y4"
    assert list(
        household.draft_events.order_by("id").values_list("action", flat=True)
    ) == ["created", "updated"]
    assert set(household.draft_events.values_list("actor_role", flat=True)) == {role}


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_forbidden_roles_cannot_create_read_or_patch(role, data, worker):
    house = create_walk_in(
        {
            "holder": {
                "first_name": "Example",
                "last_name": "Holder",
                "date_of_birth": date(1998, 5, 15),
                "phone": "+15145550123",
            }
        },
        worker,
    )
    if role.startswith("store_"):
        user = UserFactory(role=role, store=StoreFactory())
    else:
        user = UserFactory(role=role)
    client = _client(user)
    assert (
        client.post(reverse("staff-households-create"), data, format="json").status_code
        == 403
    )
    url = reverse("staff-households-detail", kwargs={"id": house.pk})
    assert client.get(url).status_code == 403
    assert (
        client.patch(
            url, {"identity_checked_in_person": True}, format="json"
        ).status_code
        == 403
    )
    assert Household.objects.count() == 1
    assert HouseholdDraftEvent.objects.count() == 1


def test_direct_service_forbids_nonstaff(worker):
    household = create_walk_in(
        {
            "holder": {
                "first_name": "Example",
                "last_name": "Holder",
                "date_of_birth": date(1998, 5, 15),
                "phone": "+15145550123",
            }
        },
        worker,
    )
    with pytest.raises(PermissionDenied):
        update_draft(
            household.pk,
            {"identity_checked_in_person": True},
            UserFactory(role="beneficiary"),
        )


def test_invalid_member_rolls_back_entire_creation(worker, data):
    from modules.households.api.serializers import WalkInDraftInputSerializer

    value = WalkInDraftInputSerializer(data=data)
    assert value.is_valid(), value.errors
    payload = deepcopy(value.validated_data)
    payload["members"][0]["date_of_birth"] = date(1800, 1, 1)
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        create_walk_in(payload, worker)
    assert Household.objects.count() == 0
    assert Member.objects.count() == 0
    assert HouseholdDraftEvent.objects.count() == 0


def test_invalid_field_is_reported_and_not_persisted(data, worker):
    client = _client(worker)
    invalid = deepcopy(data)
    invalid["address"]["postal_code"] = "invalid"
    response = client.post(reverse("staff-households-create"), invalid, format="json")
    assert response.status_code == 400
    assert "address.postal_code" in response.data["fields"]
    assert Household.objects.count() == 0


def test_unknown_privileged_fields_are_rejected(data, worker):
    client = _client(worker)
    data["status"] = "approved"
    response = client.post(reverse("staff-households-create"), data, format="json")
    assert response.status_code == 400
    assert "status" in response.data["fields"]


def test_draft_without_email_or_address_can_resume(data, worker):
    data["holder"].pop("email")
    data.pop("address")
    client = _client(worker)
    response = client.post(reverse("staff-households-create"), data, format="json")
    assert response.status_code == 201, response.data
    assert response.data["email"] is None
    assert Household.objects.get(pk=response.data["id"]).address_key == ""
    url = reverse("staff-households-detail", kwargs={"id": response.data["id"]})
    assert (
        client.patch(
            url,
            {
                "address": {
                    "street_number": "5",
                    "street_name": "rue Saint-Denis",
                    "city": "Montréal",
                    "postal_code": "H2X 1Y4",
                }
            },
            format="json",
        ).status_code
        == 200
    )


def test_non_draft_cannot_be_modified(data, worker):
    client = _client(worker)
    result = client.post(reverse("staff-households-create"), data, format="json")
    assert result.status_code == 201
    house = Household.objects.get(id=result.data["id"])
    house.status = Household.Status.SUBMITTED
    house.save(update_fields=["status"])
    url = reverse("staff-households-detail", kwargs={"id": house.pk})
    assert (
        client.patch(
            url, {"identity_checked_in_person": False}, format="json"
        ).status_code
        == 400
    )
    assert HouseholdDraftEvent.objects.count() == 1


def test_identity_check_is_only_boolean_and_staff_timestamp(data, worker):
    client = _client(worker)
    result = client.post(reverse("staff-households-create"), data, format="json")
    assert result.status_code == 201
    house = Household.objects.get(pk=result.data["id"])
    assert house.verified_by_id == worker.pk
    assert house.verified_at is not None
    assert all(
        not hasattr(house, field) for field in ("id_number", "id_document", "id_photo")
    )
    assert not hasattr(HouseholdDraftEvent, "payload")


def test_replacing_member_list_does_not_duplicate_holder(data, worker):
    client = _client(worker)
    result = client.post(reverse("staff-households-create"), data, format="json")
    url = reverse("staff-households-detail", kwargs={"id": result.data["id"]})
    reply = client.patch(url, {"members": []}, format="json")
    assert reply.status_code == 200, reply.data
    house = Household.objects.get(pk=result.data["id"])
    assert house.members.count() == 1
    assert house.members.get().relation == Member.Relation.HOLDER
