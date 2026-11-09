# AI contribution: 50% or more AI-generated
"""US-63: staff authorization, minimal results, paging and audited disclosure."""

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
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
    staff = file.created_by if role == "intake_worker" else UserFactory(role=role)
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
        "can_resume",
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
    """Return stable non-overlapping pages and audit only the disclosed records."""
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
    """Allow a metadata-only access probe without creating view events."""
    staff = UserFactory(role="admin")
    client.force_login(staff)
    response = client.head(URL, {"q": "elodie", "page_size": 9999})
    assert response.status_code == 200 and response.content == b""
    assert search_events(actor=staff.pk).count() == 0
    assert client.delete(URL).status_code == 405


@pytest.mark.parametrize(
    ("role", "allowed"),
    [
        ("intake_worker", True),
        ("admin", True),
        ("beneficiary", False),
        ("store_staff", False),
        ("store_manager", False),
    ],
)
def test_head_access_probe_uses_server_permissions_without_disclosure(
    client, file, role, allowed
):
    """Authorize the screen through the API without returning or auditing files."""
    # rule: BR-HH-ACCESS-001; BR-HH-AUDIT-001
    store = StoreFactory() if role.startswith("store_") else None
    actor = UserFactory(role=role, store=store)
    client.force_login(actor)
    response = client.head(URL)
    assert response.status_code == (200 if allowed else 403)
    assert response.content == b""
    assert search_events(actor=actor.pk).count() == 0


def test_large_page_requests_are_limited_to_100_files(client):
    """Cap disclosed and audited rows even if the client asks for a larger page."""
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
    """Roll back audit writes and withhold results if recording views fails."""
    # rule: BR-HH-AUDIT-001
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


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_ownership_and_anonymized_files_are_filtered_before_pagination(
    client, file, role
):
    # rule: BR-HH-ACCESS-001; BR-HH-ACCESS-002
    staff = UserFactory(role=role)
    assert file.created_by_id != staff.pk
    hidden = HouseholdFactory(
        created_by=staff, member_number="IR-000000", anonymized_at=timezone.now()
    )
    unassigned = HouseholdFactory(created_by=None, member_number="IR-000002")
    own = HouseholdFactory(created_by=staff, member_number="IR-000003")
    client.force_login(staff)
    expected = [file, unassigned, own] if role == "admin" else [own]
    disclosed = []
    for number in range(1, len(expected) + 1):
        page = client.get(URL, {"q": "Exemple", "page_size": 1, "page": number}).json()
        assert page["count"] == len(expected)
        disclosed.extend(row["id"] for row in page["results"])
    assert disclosed == [str(household.pk) for household in expected]
    assert set(search_events(actor=staff.pk).values_list("target_id", flat=True)) == {
        str(household.pk) for household in expected
    }
    detail = reverse("staff-households-detail", kwargs={"id": hidden.pk})
    assert client.get(detail).status_code == 404
    assert (
        client.patch(
            detail, {"address": {"unit": "5"}}, content_type="application/json"
        ).status_code
        == 404
    )


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
@pytest.mark.parametrize("channel", ["walk_in", "online"])
@pytest.mark.parametrize("status", ["draft", "approved"])
def test_resume_action_matches_the_server_edit_rule(
    client, file, role, channel, status
):
    """Keep the advertised resume capability consistent with actual PATCH permission."""
    file.channel, file.status = channel, status
    file.save(update_fields=["channel", "status"])
    staff = file.created_by if role == "intake_worker" else UserFactory(role=role)
    client.force_login(staff)
    result = client.get(URL, {"q": "elodie"}).json()["results"][0]
    expected = channel == "walk_in" and status == "draft"
    assert result["can_resume"] is expected
    response = client.patch(
        reverse("staff-households-detail", kwargs={"id": file.pk}),
        {"address": {"unit": "5"}},
        content_type="application/json",
    )
    assert response.status_code == (
        200 if expected else 404 if channel == "online" else 400
    )


def test_resume_action_is_refused_without_request_context(file):
    from modules.households.api.search_serializers import (
        HouseholdSearchResultSerializer,
    )

    assert HouseholdSearchResultSerializer(file).data["can_resume"] is False


def test_resume_flags_do_not_add_a_database_query_per_result(client):
    """Bound database work independently of the number of returned resume flags."""
    staff = UserFactory(role="intake_worker")
    Household.objects.bulk_create(
        [
            Household(
                email=f"resume-budget-{i}@example.test",
                phone="+15145550100",
                created_by=staff,
            )
            for i in range(20)
        ]
    )
    client.force_login(staff)
    client.head(URL, {"q": "resume-budget-"})
    with CaptureQueriesContext(connection) as one:
        first = client.get(URL, {"q": "resume-budget-", "page_size": 1})
    with CaptureQueriesContext(connection) as twenty:
        page = client.get(URL, {"q": "resume-budget-", "page_size": 20})
    assert first.status_code == page.status_code == 200
    assert len(first.json()["results"]) == 1
    assert len(page.json()["results"]) == 20
    assert all(row["can_resume"] for row in page.json()["results"])
    assert len(twenty) == len(one)
    household_reads = [
        entry
        for entry in twenty
        if entry["sql"].lstrip().startswith("SELECT")
        and '"households_household"' in entry["sql"]
    ]
    assert len(household_reads) == 1


@pytest.mark.parametrize("page", ["0", "-1", "1.5", "unknown", "9" * 80])
def test_invalid_search_page_numbers_are_refused_without_audit(client, file, page):
    staff = UserFactory(role="intake_worker")
    client.force_login(staff)
    response = client.get(URL, {"q": "elodie", "page": page})
    assert response.status_code == 404
    assert search_events(actor=staff.pk).count() == 0


def test_last_page_shortcut_keeps_the_expected_count_and_links(client):
    """Retain the last-page shortcut and exact response links after count optimization."""
    files = [HouseholdFactory(member_number=f"IR-{i:06d}") for i in range(3)]
    client.force_login(UserFactory(role="admin"))
    response = client.get(URL, {"q": "Exemple", "page": "last", "page_size": 2})
    assert response.status_code == 200
    page = response.json()
    assert page["count"] == 3
    assert [row["id"] for row in page["results"]] == [str(files[2].pk)]
    assert page["next"] is None and page["previous"] is not None
