# AI contribution: 50% or more AI-generated
"""POST /api/staff/households/{id}/notices/ (T-03.18.2, tests for #467).

The main path runs through the API, the database and the file store, then
opens the stored file through its signed link.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from adapters.file_store.memory import InMemoryFileStore
from modules.documents import services as document_services
from modules.documents.queries import current_notices
from modules.households.models import Household, HouseholdDraftEvent
from modules.households.notice_services import record_walk_in_notice
from modules.households.tests.factories import MemberFactory
from modules.households.tests.notices.helpers import (
    CONTENT,
    NOTICE_FIELDS,
    api_client,
    filed_notice,
    make_user,
    pdf_upload,
    post_notice,
    publish_notice_rule,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_staff_record_a_notice_end_to_end(
    household: Any, holder: Any, role: str
) -> None:
    client = api_client(make_user(role))

    response = post_notice(client, household, filed_notice(holder))

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

    response = post_notice(api_client(worker), household, data)

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

    response = post_notice(api_client(worker), household, data)

    assert response.status_code == 201, response.data
    assert response.data["status"] == "did_not_file"


@pytest.mark.parametrize("field", [*NOTICE_FIELDS, "file"])
def test_br_doc_001_each_missing_field_is_reported(
    household: Any, holder: Any, worker: Any, field: str
) -> None:
    response = post_notice(
        api_client(worker), household, filed_notice(holder, **{field: None})
    )

    assert response.status_code == 400
    assert field in response.data["fields"]
    assert not current_notices([holder.pk])


def test_seen_in_person_false_is_an_answer(
    household: Any, holder: Any, worker: Any
) -> None:
    response = post_notice(
        api_client(worker), household, filed_notice(holder, seen_in_person="false")
    )

    assert response.status_code == 201, response.data
    assert response.data["seen_in_person"] is False


def test_br_doc_004_disguised_file_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    disguised = pdf_upload(b"<html><script>alert(1)</script>")

    response = post_notice(
        api_client(worker), household, filed_notice(holder, file=disguised)
    )

    assert response.status_code == 400
    assert "file" in response.data["fields"]
    assert InMemoryFileStore.references() == []


def test_br_doc_004_file_over_the_rule_limit_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    publish_notice_rule(max_bytes=8)

    response = post_notice(api_client(worker), household, filed_notice(holder))

    assert response.status_code == 400
    assert "file" in response.data["fields"]


def test_br_doc_007_child_is_refused(
    household: Any, holder: Any, child: Any, worker: Any
) -> None:
    response = post_notice(api_client(worker), household, filed_notice(child))

    assert response.status_code == 400
    assert "member" in response.data["fields"]
    assert InMemoryFileStore.references() == []


def withdraw_consent(household: Any) -> None:
    Household.objects.filter(pk=household.pk).update(
        consent_data_processing_at=None, consent_text_version=""
    )


def assert_nothing_kept(household: Any, holder: Any) -> None:
    assert current_notices([holder.pk]) == {}
    assert InMemoryFileStore.references() == []
    assert not HouseholdDraftEvent.objects.filter(household=household).exists()


def test_prv_02_notice_is_refused_until_the_household_consents(
    household: Any, holder: Any, worker: Any, monkeypatch: Any
) -> None:
    withdraw_consent(household)
    uploads: list[Any] = []
    monkeypatch.setattr(
        document_services, "prepare_staff_notice", lambda *args: uploads.append(args)
    )

    response = post_notice(
        api_client(worker), household, filed_notice(holder), HTTP_ACCEPT_LANGUAGE="fr"
    )

    assert response.status_code == 400
    assert response.data["fields"] == {
        "consent_data_processing": [
            "Enregistrez le consentement du foyer avant d'ajouter un avis."
        ]
    }
    assert uploads == []  # refused before the file reaches storage
    assert_nothing_kept(household, holder)


def test_prv_02_consent_withdrawn_during_the_upload_still_refuses(
    household: Any, holder: Any, worker: Any, monkeypatch: Any
) -> None:
    """The check under the row lock catches consent removed after the first one."""
    prepare = document_services.prepare_staff_notice

    def prepare_then_withdraw(*args: Any) -> Any:
        prepared = prepare(*args)
        withdraw_consent(household)
        return prepared

    monkeypatch.setattr(
        document_services, "prepare_staff_notice", prepare_then_withdraw
    )

    response = post_notice(api_client(worker), household, filed_notice(holder))

    assert response.status_code == 400
    assert list(response.data["fields"]) == ["consent_data_processing"]
    assert_nothing_kept(household, holder)


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

    response = post_notice(api_client(worker), household, filed_notice(member))

    assert response.status_code == status, response.data


def test_member_of_another_household_is_refused(
    household: Any, holder: Any, worker: Any
) -> None:
    other: Any = MemberFactory(relation="spouse_partner", date_of_birth="1980-01-01")

    response = post_notice(api_client(worker), household, filed_notice(other))

    assert response.status_code == 400
    assert "member" in response.data["fields"]
    assert not current_notices([other.pk])


def test_unknown_household_is_404(holder: Any, worker: Any) -> None:
    url = reverse(
        "staff-households-notices",
        kwargs={"id": "00000000-0000-0000-0000-000000000000"},
    )

    response = api_client(worker).post(url, filed_notice(holder), format="multipart")

    assert response.status_code == 404


# rule: BR-DOC-007
@pytest.mark.parametrize(
    "status",
    [
        Household.Status.SUBMITTED,
        Household.Status.REVIEW_REQUIRED,
        Household.Status.APPROVED,
        Household.Status.REJECTED,
    ],
)
def test_non_draft_household_is_refused(
    household: Any, holder: Any, worker: Any, status: str
) -> None:
    Household.objects.filter(pk=household.pk).update(status=status)

    response = post_notice(api_client(worker), household, filed_notice(holder))

    assert response.status_code == 400
    assert "status" in response.data["fields"]


def test_name_and_postal_code_are_normalized(
    household: Any, holder: Any, worker: Any
) -> None:
    data = filed_notice(
        holder, name_on_notice="Émilie D’Amours", postal_code_on_notice="h2x1y4"
    )

    response = post_notice(api_client(worker), household, data)

    assert response.status_code == 201, response.data
    notice = current_notices([holder.pk])[holder.pk]
    assert notice.name_on_notice == "Émilie D’Amours"
    assert notice.postal_code_on_notice == "H2X 1Y4"


def test_unknown_fields_are_refused(household: Any, holder: Any, worker: Any) -> None:
    response = post_notice(
        api_client(worker), household, filed_notice(holder, status="confirmed")
    )

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
    response = post_notice(
        api_client(make_user(role, active=active)), household, filed_notice(holder)
    )

    assert response.status_code == 403
    assert not current_notices([holder.pk])


def test_signed_out_visitors_are_refused(household: Any, holder: Any) -> None:
    response = post_notice(api_client(None), household, filed_notice(holder))

    assert response.status_code == 401
    assert not current_notices([holder.pk])


@override_settings(FILE_STORE_BACKEND="")
def test_storage_down_answers_503(household: Any, holder: Any, worker: Any) -> None:
    response = post_notice(api_client(worker), household, filed_notice(holder))

    assert response.status_code == 503
    assert response.data["code"] == "storage_unavailable"
    assert not current_notices([holder.pk])
    assert not HouseholdDraftEvent.objects.filter(household=household).exists()


def test_errors_follow_the_request_language(
    household: Any, holder: Any, worker: Any
) -> None:
    response = post_notice(
        api_client(worker),
        household,
        filed_notice(holder, tax_year=None),
        HTTP_ACCEPT_LANGUAGE="fr",
    )

    assert response.status_code == 400
    assert response.data["fields"]["tax_year"] == ["Entrez cette information."]


def test_a_second_entry_replaces_the_current_notice(
    household: Any, holder: Any, worker: Any
) -> None:
    client = api_client(worker)
    first = post_notice(client, household, filed_notice(holder))
    data = {
        "member": str(holder.pk),
        "did_not_file": "true",
        "did_not_file_reason": "Typed by mistake before",
    }

    second = post_notice(client, household, data)

    assert second.status_code == 201
    current = current_notices([holder.pk])[holder.pk]
    assert str(current.pk) == second.data["id"] != first.data["id"]


def test_notice_date_is_checked_against_today(
    household: Any, holder: Any, worker: Any
) -> None:
    tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()

    response = post_notice(
        api_client(worker), household, filed_notice(holder, notice_date=tomorrow)
    )

    assert response.status_code == 400
    assert "notice_date" in response.data["fields"]
    assert date.fromisoformat(tomorrow) > timezone.localdate()


def test_household_errors_are_translated(
    household: Any, holder: Any, child: Any, worker: Any
) -> None:
    response = post_notice(
        api_client(worker), household, filed_notice(child), HTTP_ACCEPT_LANGUAGE="fr"
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
