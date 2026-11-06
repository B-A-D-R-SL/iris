# AI contribution: 50% or more AI-generated
"""POST /api/staff/households/{id}/notices/ (T-03.18.2, tests for #467).

The main path runs through the API, the database and the file store, then
opens the stored file through its signed link.
"""

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from adapters.file_store.memory import InMemoryFileStore
from modules.accounts.tests.factories import UserFactory
from modules.documents.queries import current_notices
from modules.households.models import Household, HouseholdDraftEvent
from modules.households.services import record_walk_in_notice
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

CONTENT = b"%PDF-1.7 walk-in"
NOTICE_FIELDS = (
    "tax_year",
    "total_income_cents",
    "name_on_notice",
    "postal_code_on_notice",
    "notice_date",
    "seen_in_person",
)


# Fixed, not relative to timezone.now(): tests that pin the clock still find the rule.
RULE_EFFECTIVE_FROM = datetime(2020, 1, 1, tzinfo=UTC)


def _publish_rule(**changes: Any) -> None:
    values = deepcopy(DEFAULT_RULE_VALUES["notice_upload"]) | changes
    # A version with changes takes effect after the default one.
    effective = RULE_EFFECTIVE_FROM + timedelta(minutes=len(changes))
    publisher: Any = UserFactory(role="admin")
    publish("notice_upload", values, publisher, effective_from=effective)


@pytest.fixture(autouse=True)
def _notice_rule() -> None:
    _publish_rule()


@pytest.fixture
def worker() -> Any:
    return UserFactory(role="intake_worker")


@pytest.fixture
def household() -> Any:
    return HouseholdFactory()


@pytest.fixture
def holder(household: Any) -> Any:
    return MemberFactory(
        household=household, relation="holder", date_of_birth="1990-01-01"
    )


@pytest.fixture
def child(household: Any) -> Any:
    return MemberFactory(
        household=household, relation="child", date_of_birth="2016-03-01"
    )


def _client(user: Any | None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _pdf(content: bytes = CONTENT, name: str = "scan.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _filed(member: Any, **changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "member": str(member.pk),
        "file": _pdf(),
        "tax_year": "2025",
        "total_income_cents": "2345600",
        "name_on_notice": "Example Holder",
        "postal_code_on_notice": "H2X 1Y4",
        "notice_date": "2026-04-30",
        "seen_in_person": "true",
    }
    values.update(changes)
    return {key: value for key, value in values.items() if value is not None}


def _post(client: APIClient, household: Any, data: dict[str, Any], **extra: Any) -> Any:
    url = reverse("staff-households-notices", kwargs={"id": household.pk})
    return client.post(url, data, format="multipart", **extra)


def _make_user(role: str, *, active: bool = True) -> Any:
    store = StoreFactory() if role.startswith("store_") else None
    return UserFactory(role=role, is_active=active, store=store)


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_staff_record_a_notice_end_to_end(
    household: Any, holder: Any, role: str
) -> None:
    client = _client(_make_user(role))

    response = _post(client, household, _filed(holder))

    assert response.status_code == 201, response.data
    assert response.data["member"] == str(holder.pk)
    assert response.data["status"] == "confirmed"
    assert response.data["source"] == "staff"
    assert response.data["total_income_cents"] == 2_345_600
    assert response.data["has_file"] is True
    assert "file_ref" not in response.data
    notice = current_notices([holder.pk])[holder.pk]
    assert str(notice.pk) == response.data["id"]
    assert HouseholdDraftEvent.objects.filter(
        household=household, action=HouseholdDraftEvent.Action.UPDATED
    ).exists()

    link = client.get(reverse("staff-notice-file-link", kwargs={"id": notice.pk}))
    download = client.get(link.data["url"])

    assert download.status_code == 200
    assert download.content == CONTENT


def test_did_not_file_is_recorded(household: Any, holder: Any, worker: Any) -> None:
    data = {
        "member": str(holder.pk),
        "did_not_file": "true",
        "did_not_file_reason": "No income in 2025",
    }

    response = _post(_client(worker), household, data)

    assert response.status_code == 201, response.data
    assert response.data["status"] == "did_not_file"
    assert response.data["has_file"] is False
    assert response.data["did_not_file_reason"] == "No income in 2025"


def test_did_not_file_with_empty_form_fields_is_accepted(
    household: Any, holder: Any, worker: Any
) -> None:
    data = {
        "member": str(holder.pk),
        "did_not_file": "true",
        "did_not_file_reason": "No income in 2025",
        "file": "",
        "tax_year": "",
        "total_income_cents": "",
        "name_on_notice": "",
        "postal_code_on_notice": "",
        "notice_date": "",
        "seen_in_person": "false",
    }

    response = _post(_client(worker), household, data)

    assert response.status_code == 201, response.data
    assert response.data["status"] == "did_not_file"


@pytest.mark.parametrize("field", [*NOTICE_FIELDS, "file"])
def test_br_doc_001_each_missing_field_is_reported(
    household: Any, holder: Any, worker: Any, field: str
) -> None:
    response = _post(_client(worker), household, _filed(holder, **{field: None}))

    assert response.status_code == 400
    assert field in response.data["fields"]
    assert not current_notices([holder.pk])


def test_seen_in_person_false_is_an_answer(
    household: Any, holder: Any, worker: Any
) -> None:
    response = _post(_client(worker), household, _filed(holder, seen_in_person="false"))

    assert response.status_code == 201, response.data
    assert response.data["seen_in_person"] is False


def test_br_doc_004_disguised_file_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    disguised = _pdf(b"<html><script>alert(1)</script>")

    response = _post(_client(worker), household, _filed(holder, file=disguised))

    assert response.status_code == 400
    assert "file" in response.data["fields"]
    assert InMemoryFileStore.references() == []


def test_br_doc_004_file_over_the_rule_limit_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    _publish_rule(max_bytes=8)

    response = _post(_client(worker), household, _filed(holder))

    assert response.status_code == 400
    assert "file" in response.data["fields"]


def test_br_doc_007_child_is_refused(
    household: Any, holder: Any, child: Any, worker: Any
) -> None:
    response = _post(_client(worker), household, _filed(child))

    assert response.status_code == 400
    assert "member" in response.data["fields"]
    assert InMemoryFileStore.references() == []


@pytest.mark.parametrize(
    ("birth", "status"), [("2008-06-15", 201), ("2008-06-16", 400)]
)
def test_br_doc_007_eighteenth_birthday_today_is_adult(
    household: Any,
    worker: Any,
    monkeypatch: pytest.MonkeyPatch,
    birth: str,
    status: int,
) -> None:
    # A pinned day long before the real run date: the rule fixture must not
    # depend on the real clock (review finding).
    monkeypatch.setattr(timezone, "now", lambda: datetime(2026, 6, 15, 17, tzinfo=UTC))
    member = MemberFactory(
        household=household, relation="spouse_partner", date_of_birth=birth
    )

    response = _post(_client(worker), household, _filed(member))

    assert response.status_code == status, response.data


def test_member_of_another_household_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    other: Any = MemberFactory(relation="spouse_partner", date_of_birth="1980-01-01")

    response = _post(_client(worker), household, _filed(other))

    assert response.status_code == 400
    assert "member" in response.data["fields"]
    assert not current_notices([other.pk])


def test_unknown_household_is_404(holder: Any, worker: Any) -> None:
    url = reverse(
        "staff-households-notices",
        kwargs={"id": "00000000-0000-0000-0000-000000000000"},
    )

    response = _client(worker).post(url, _filed(holder), format="multipart")

    assert response.status_code == 404


def test_non_draft_household_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    Household.objects.filter(pk=household.pk).update(status=Household.Status.SUBMITTED)

    response = _post(_client(worker), household, _filed(holder))

    assert response.status_code == 400
    assert "status" in response.data["fields"]


def test_name_and_postal_code_are_normalized(
    household: Any, holder: Any, worker: Any
) -> None:
    data = _filed(
        holder, name_on_notice="Émilie D’Amours", postal_code_on_notice="h2x1y4"
    )

    response = _post(_client(worker), household, data)

    assert response.status_code == 201, response.data
    notice = current_notices([holder.pk])[holder.pk]
    assert notice.name_on_notice == "Émilie D’Amours"
    assert notice.postal_code_on_notice == "H2X 1Y4"


def test_unknown_fields_are_refused(household: Any, holder: Any, worker: Any) -> None:
    response = _post(_client(worker), household, _filed(holder, status="confirmed"))

    assert response.status_code == 400
    assert "status" in response.data["fields"]


@pytest.mark.parametrize(
    ("role", "active"),
    [
        ("beneficiary", True),
        ("store_staff", True),
        ("store_manager", True),
        ("intake_worker", False),
    ],
)
def test_other_roles_are_refused(
    household: Any, holder: Any, role: str, active: bool
) -> None:
    response = _post(
        _client(_make_user(role, active=active)), household, _filed(holder)
    )

    assert response.status_code == 403
    assert not current_notices([holder.pk])


def test_signed_out_visitors_are_refused(household: Any, holder: Any) -> None:
    response = _post(_client(None), household, _filed(holder))

    assert response.status_code == 401
    assert not current_notices([holder.pk])


@override_settings(FILE_STORE_BACKEND="")
def test_storage_down_answers_503(household: Any, holder: Any, worker: Any) -> None:
    response = _post(_client(worker), household, _filed(holder))

    assert response.status_code == 503
    assert response.data["code"] == "storage_unavailable"
    assert not current_notices([holder.pk])
    assert not HouseholdDraftEvent.objects.filter(household=household).exists()


def test_errors_follow_the_request_language(
    household: Any, holder: Any, worker: Any
) -> None:
    response = _post(
        _client(worker),
        household,
        _filed(holder, tax_year=None),
        HTTP_ACCEPT_LANGUAGE="fr",
    )

    assert response.status_code == 400
    assert response.data["fields"]["tax_year"] == ["Entrez cette information."]


def test_a_second_entry_replaces_the_current_notice(
    household: Any, holder: Any, worker: Any
) -> None:
    client = _client(worker)
    first = _post(client, household, _filed(holder))
    data = {
        "member": str(holder.pk),
        "did_not_file": "true",
        "did_not_file_reason": "Typed by mistake before",
    }

    second = _post(client, household, data)

    assert second.status_code == 201
    current = current_notices([holder.pk])[holder.pk]
    assert str(current.pk) == second.data["id"] != first.data["id"]


def test_notice_date_is_checked_against_today(
    household: Any, holder: Any, worker: Any
) -> None:
    tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()

    response = _post(_client(worker), household, _filed(holder, notice_date=tomorrow))

    assert response.status_code == 400
    assert "notice_date" in response.data["fields"]
    assert date.fromisoformat(tomorrow) > timezone.localdate()


def test_household_errors_are_translated(
    household: Any, holder: Any, child: Any, worker: Any
) -> None:
    response = _post(
        _client(worker), household, _filed(child), HTTP_ACCEPT_LANGUAGE="fr"
    )

    assert response.data["fields"]["member"] == [
        "Les avis sont enregistrés seulement pour les adultes."
    ]


def test_service_requires_a_member_id(household: Any, worker: Any) -> None:
    with pytest.raises(ValidationError) as caught:
        record_walk_in_notice(household.pk, {"did_not_file": True}, worker)

    assert set(caught.value.message_dict) == {"member"}


def test_schema_documents_the_notice_file_as_binary(client: Any) -> None:
    response = client.get("/api/schema/", {"format": "json"})

    schema = response.json()["components"]["schemas"]["WalkInNoticeInput"]
    assert schema["properties"]["file"]["format"] == "binary"


SPOUSE = {
    "first_name": "Example",
    "last_name": "Spouse",
    "date_of_birth": "1985-02-03",
    "relation": "spouse_partner",
}


def _spouse_with_notice(household: Any, worker: Any) -> Any:
    spouse: Any = MemberFactory(household=household, **SPOUSE)
    data = {
        "member": str(spouse.pk),
        "did_not_file": "true",
        "did_not_file_reason": "No income in 2025",
    }
    assert _post(_client(worker), household, data).status_code == 201
    return spouse


def _save_members(worker: Any, household: Any, members: list[dict[str, Any]]) -> Any:
    url = reverse("staff-households-detail", kwargs={"id": household.pk})
    return _client(worker).patch(url, {"members": members}, format="json")


def test_adding_a_member_keeps_members_with_notices(
    household: Any, holder: Any, worker: Any
) -> None:
    spouse = _spouse_with_notice(household, worker)
    newborn = {
        "first_name": "Example",
        "last_name": "Baby",
        "date_of_birth": "2026-01-15",
        "relation": "child",
    }

    response = _save_members(worker, household, [SPOUSE, newborn])

    assert response.status_code == 200, response.data
    assert household.members.count() == 3
    assert household.members.filter(pk=spouse.pk).exists()
    assert spouse.pk in current_notices([spouse.pk])


def test_removing_a_member_with_a_notice_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    spouse = _spouse_with_notice(household, worker)

    response = _save_members(worker, household, [])

    assert response.status_code == 400
    assert "members" in response.data["fields"]
    assert household.members.filter(pk=spouse.pk).exists()
