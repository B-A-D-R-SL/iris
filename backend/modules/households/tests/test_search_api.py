# AI contribution: 50% or more AI-generated
"""US-63: staff authorization, minimal results, paging and audited disclosure."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.audit.queries import search_events
from modules.households.models import Household, Member
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db
URL = reverse("staff-households-create")


@pytest.fixture
def file():
    household = HouseholdFactory(member_number="IR-000001")
    MemberFactory(
        household=household,
        first_name="Élodie",
        last_name="Exemple",
        relation=Member.Relation.HOLDER,
    )
    return household


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_staff_searches_through_session_authentication(client, file, role):
    staff = UserFactory(role=role)
    client.force_login(staff)
    response = client.get(URL, {"q": "elodie"})
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["id"] == str(file.pk)
    assert result["first_name"] == "Élodie"
    assert result["member_number"] == "IR-000001"
    assert set(result) == {
        "id",
        "member_number",
        "first_name",
        "last_name",
        "status",
        "channel",
        "email",
        "phone",
        "street_number",
        "street_name",
        "unit",
        "city",
        "postal_code",
    }
    assert response["Cache-Control"] == "private, no-store"
    event = search_events(actor=staff.pk).get()
    assert (event.action, event.target_type, event.target_id, event.metadata) == (
        "view",
        "household",
        str(file.pk),
        {},
    )


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_other_roles_cannot_search(client, file, role):
    store = StoreFactory() if role.startswith("store_") else None
    user = UserFactory(role=role, store=store)
    client.force_login(user)
    assert client.get(URL, {"q": "elodie"}).status_code == 403
    assert search_events(actor=user.pk).count() == 0


def test_anonymous_and_inactive_staff_are_refused(client, file):
    assert client.get(URL, {"q": "elodie"}).status_code in (401, 403)
    inactive = UserFactory(role="admin", is_active=False)
    api_client = APIClient()
    api_client.force_authenticate(inactive)
    assert api_client.get(URL, {"q": "elodie"}).status_code == 403


@pytest.mark.parametrize("query", ["x" * 255, "\x00"])
def test_invalid_search_input_is_rejected(client, query):
    client.force_login(UserFactory(role="intake_worker"))
    response = client.get(URL, {"q": query})
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "q" in response.json()["fields"]


@pytest.mark.parametrize("query", [{}, {"q": ""}, {"q": "  "}, {"q": "missing-file"}])
def test_blank_and_unmatched_searches_do_not_disclose_or_audit_files(
    client, file, query
):
    staff = UserFactory(role="intake_worker")
    client.force_login(staff)
    response = client.get(URL, query)
    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }
    assert search_events(actor=staff.pk).count() == 0


def test_pagination_has_stable_order_and_audits_only_returned_files(client):
    staff = UserFactory(role="intake_worker")
    files = [
        HouseholdFactory(created_by=staff, member_number=f"IR-{i:06d}")
        for i in range(3)
    ]
    client.force_login(staff)
    first = client.get(URL, {"q": "Exemple", "page_size": 2}).json()
    second = client.get(URL, {"q": "Exemple", "page_size": 2, "page": 2}).json()
    assert first["count"] == 3 and first["next"] is not None
    assert second["previous"] is not None and second["next"] is None
    assert [row["id"] for row in first["results"] + second["results"]] == [
        str(f.pk) for f in files
    ]
    assert search_events(actor=staff.pk).count() == 3
    assert client.get(URL, {"q": "Exemple", "page": 999}).status_code == 404


def test_page_size_is_capped_and_head_does_not_create_view_events(client, file):
    staff = UserFactory(role="admin")
    client.force_login(staff)
    response = client.head(URL, {"q": "elodie", "page_size": 9999})
    assert response.status_code == 200 and response.content == b""
    assert search_events(actor=staff.pk).count() == 0
    assert client.delete(URL).status_code == 405


def test_large_page_requests_are_limited_to_100_files(client):
    staff = UserFactory(role="admin")
    Household.objects.bulk_create(
        [
            Household(email=f"page-cap-{i}@example.test", phone="+15145550100")
            for i in range(105)
        ]
    )
    client.force_login(staff)
    response = client.get(URL, {"q": "page-cap-", "page_size": 9999})
    assert response.status_code == 200
    assert response.json()["count"] == 105
    assert len(response.json()["results"]) == 100
    assert search_events(actor=staff.pk).count() == 100


def test_audit_failure_prevents_disclosure_and_rolls_back_events(
    client, file, monkeypatch
):
    from modules.households.api import views

    staff = UserFactory(role="admin")
    client.force_login(staff)
    original = views.audit_services.record_household_views

    def fail_after_insert(*args, **kwargs):
        original(*args, **kwargs)
        raise ValidationError("Audit unavailable")

    monkeypatch.setattr(
        views.audit_services, "record_household_views", fail_after_insert
    )
    with pytest.raises(ValidationError, match="Audit unavailable"):
        client.get(URL, {"q": "elodie"})
    assert search_events(actor=staff.pk).count() == 0
    assert Household.objects.filter(pk=file.pk).count() == 1
