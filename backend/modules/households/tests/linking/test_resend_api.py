# AI contribution: 50% or more AI-generated
"""POST /api/staff/households/{id}/resend-invitation/ (US-93).

resend_invitation has its own tests; these check access and the HTTP contract.
"""

from typing import Any
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.households.tests.approval.helpers import invitations
from modules.households.tests.linking.helpers import account, approved_walk_in
from modules.stores.tests.factories import StoreFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]


def resend_url(household_id: object) -> str:
    return f"/api/staff/households/{household_id}/resend-invitation/"


def signed_in(user: Any) -> APIClient:
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def origin(settings: Any) -> None:
    settings.PUBLIC_APP_ORIGIN = "https://iris.example.test"


def test_resend_through_api_and_database(staff: Any) -> None:
    household = approved_walk_in(staff)
    response = signed_in(staff).post(resend_url(household.pk), {}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "invited"
    assert invitations().get().household_id == household.pk


def test_admin_can_resend(staff: Any) -> None:
    household = approved_walk_in(staff)
    admin = UserFactory(role="admin")
    response = signed_in(admin).post(resend_url(household.pk), {}, format="json")
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_other_roles_get_403(staff: Any, role: str) -> None:
    household = approved_walk_in(staff)
    store = StoreFactory() if role.startswith("store") else None
    other = UserFactory(role=role, store=store)
    response = signed_in(other).post(resend_url(household.pk), {}, format="json")
    assert response.status_code == 403
    assert not invitations().exists()


def test_anonymous_gets_401(staff: Any) -> None:
    household = approved_walk_in(staff)
    response = APIClient().post(resend_url(household.pk), {}, format="json")
    assert response.status_code == 401


def test_unknown_file_is_404(staff: Any) -> None:
    response = signed_in(staff).post(resend_url(uuid4()), {}, format="json")
    assert response.status_code == 404


def test_resend_refuses_unknown_fields(staff: Any) -> None:
    household = approved_walk_in(staff)
    response = signed_in(staff).post(
        resend_url(household.pk), {"email": "x@example.test"}, format="json"
    )
    assert response.status_code == 400
    assert not invitations().exists()


def test_resend_refusal_is_400_with_message(staff: Any) -> None:
    household = approved_walk_in(staff)
    account()
    response = signed_in(staff).post(resend_url(household.pk), {}, format="json")
    assert response.status_code == 400
    assert response.json()["fields"] == {
        "non_field_errors": [
            (
                "This email address already has an Iris account. "
                "Link that account instead of sending an invitation."
            )
        ]
    }
