# AI contribution: 50% or more AI-generated
"""POST /api/staff/households/{id}/link-account/ and the detail's account (US-93).

link_existing_account has its own tests; these check access, the HTTP contract
and the account state the staff screens read.
"""

from typing import Any
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.tests.approval.helpers import audit_events
from modules.households.tests.linking.helpers import account, approved_walk_in
from modules.rules.services import publish
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db
CONFIRMED = {"identity_confirmed": True}


def link_url(household_id: object) -> str:
    return f"/api/staff/households/{household_id}/link-account/"


def signed_in(user: Any) -> APIClient:
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_login(user)
    return client


# rule: BR-HH-ACCOUNT-002
@pytest.mark.parametrize("body", [{}, {"identity_confirmed": False}])
def test_link_requires_identity_confirmation(staff: Any, body: dict[str, Any]) -> None:
    household = approved_walk_in(staff)
    account()
    response = signed_in(staff).post(link_url(household.pk), body, format="json")
    assert response.status_code == 400
    assert "identity_confirmed" in response.json()["fields"]
    household.refresh_from_db()
    assert household.holder_id is None


def test_link_refuses_unknown_fields(staff: Any) -> None:
    household = approved_walk_in(staff)
    account()
    body = CONFIRMED | {"holder": str(uuid4())}
    response = signed_in(staff).post(link_url(household.pk), body, format="json")
    assert response.status_code == 400


def test_link_through_api_and_database(staff: Any) -> None:
    household = approved_walk_in(staff)
    user = account()
    response = signed_in(staff).post(link_url(household.pk), CONFIRMED, format="json")
    assert response.status_code == 200
    assert response.json() == {
        "status": "linked",
        "reason": "",
        "account_first_name": None,
        "account_last_name": None,
    }
    household.refresh_from_db()
    assert household.holder_id == user.pk
    assert audit_events(household).filter(action="link_account").count() == 1


def test_admin_can_link(staff: Any) -> None:
    household = approved_walk_in(staff)
    account()
    admin = UserFactory(role="admin")
    response = signed_in(admin).post(link_url(household.pk), CONFIRMED, format="json")
    assert response.status_code == 200


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_other_roles_get_403(staff: Any, role: str) -> None:
    household = approved_walk_in(staff)
    account()
    store = StoreFactory() if role.startswith("store") else None
    other = UserFactory(role=role, store=store)
    response = signed_in(other).post(link_url(household.pk), CONFIRMED, format="json")
    assert response.status_code == 403
    household.refresh_from_db()
    assert household.holder_id is None


def test_anonymous_gets_401(staff: Any) -> None:
    household = approved_walk_in(staff)
    response = APIClient().post(link_url(household.pk), CONFIRMED, format="json")
    assert response.status_code == 401


def test_inactive_staff_is_refused(staff: Any) -> None:
    household = approved_walk_in(staff)
    account()
    inactive = UserFactory(role="intake_worker", is_active=False)
    response = signed_in(inactive).post(
        link_url(household.pk), CONFIRMED, format="json"
    )
    assert response.status_code in (401, 403)


def test_unknown_or_online_file_is_404(staff: Any) -> None:
    online = approved_walk_in(staff, channel=Household.Channel.ONLINE)
    account()
    client = signed_in(staff)
    assert client.post(link_url(uuid4()), CONFIRMED, format="json").status_code == 404
    assert client.post(link_url(online.pk), CONFIRMED, format="json").status_code == 404


def test_link_refusal_is_400_with_message(staff: Any) -> None:
    household = approved_walk_in(staff)
    response = signed_in(staff).post(link_url(household.pk), CONFIRMED, format="json")
    assert response.status_code == 400
    assert response.json()["fields"] == {
        "non_field_errors": ["No Iris account uses this file's email address."]
    }


def test_detail_includes_account_state(staff: Any) -> None:
    # The detail also reports the suspension reason limit, so the rule must exist.
    admin: Any = UserFactory(role="admin")
    publish("household_suspension", {"reason_max_length": 500}, admin)
    household = approved_walk_in(staff)
    account()
    client = signed_in(staff)
    detail = client.get(f"/api/staff/households/{household.pk}/").json()
    assert detail["account"] == {
        "status": "can_link",
        "reason": "",
        "account_first_name": "Samira",
        "account_last_name": "Example",
    }
    draft = approved_walk_in(staff, status=Household.Status.DRAFT, email=None)
    detail = client.get(f"/api/staff/households/{draft.pk}/").json()
    assert detail["account"]["status"] == "not_applicable"
