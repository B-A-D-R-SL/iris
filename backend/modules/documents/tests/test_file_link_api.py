# AI contribution: 50% or more AI-generated
"""Signed staff links and downloads for notice files, BR-DOC-006 (T-03.18.2, #467)."""

from datetime import date, timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from adapters.file_store.memory import InMemoryFileStore
from modules.audit.queries import search_events
from modules.documents.models import IncomeNotice
from modules.documents.services import record_staff_notice
from modules.documents.tests.factories import make_member, make_user

pytestmark = pytest.mark.django_db

CONTENT = b"%PDF-1.7 test"
FILED = {
    "tax_year": 2025,
    "total_income_cents": 4_321_000,
    "name_on_notice": "Example Holder",
    "postal_code_on_notice": "H2X 1Y4",
    "notice_date": date(2026, 4, 30),
    "seen_in_person": True,
}


def _client(user: Any | None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _link(client: APIClient, notice_id: Any) -> Any:
    return client.get(reverse("staff-notice-file-link", kwargs={"id": notice_id}))


def _record(worker: Any, member: Any | None = None, **values: Any) -> IncomeNotice:
    upload = SimpleUploadedFile("scan.pdf", CONTENT, content_type="application/pdf")
    return record_staff_notice(
        (member or make_member()).pk, FILED | values, upload, worker
    )


@pytest.fixture
def notice(notice_rule: None, worker: Any) -> IncomeNotice:
    return _record(worker)


@pytest.mark.parametrize("role", ["intake_worker", "admin"])
def test_staff_get_a_link_and_download_the_same_bytes(
    notice: IncomeNotice, role: str
) -> None:
    client = _client(make_user(role))

    link = _link(client, notice.pk)

    assert link.status_code == 200, link.data
    assert link.data["url"].startswith("/api/staff/notice-files/")
    expires_at = parse_datetime(link.data["expires_at"])
    assert expires_at is not None
    expected = timezone.now() + timedelta(minutes=5)
    assert abs(expires_at - expected) < timedelta(seconds=5)

    download = client.get(link.data["url"])

    assert download.status_code == 200
    assert download.content == CONTENT
    assert download["Content-Type"] == "application/pdf"
    assert download["Content-Disposition"] == 'attachment; filename="notice-2025.pdf"'
    assert download["X-Content-Type-Options"] == "nosniff"
    assert download["Cache-Control"] == "private, no-store"


def test_br_doc_006_link_issue_is_audited_without_metadata(
    notice: IncomeNotice, worker: Any
) -> None:
    _link(_client(worker), notice.pk)

    (event,) = search_events(actor=worker.pk)
    assert (event.action, event.target_type) == ("view", "income_notice")
    assert event.target_id == str(notice.pk)
    assert event.metadata == {}


@pytest.mark.parametrize(
    ("role", "active"),
    [
        ("beneficiary", True),
        ("store_staff", True),
        ("store_manager", True),
        ("admin", False),
    ],
)
def test_other_roles_are_refused(
    notice: IncomeNotice, worker: Any, role: str, active: bool
) -> None:
    url = _link(_client(worker), notice.pk).data["url"]
    client = _client(make_user(role, active=active))

    assert _link(client, notice.pk).status_code == 403
    assert client.get(url).status_code == 403


def test_signed_out_visitors_are_refused(notice: IncomeNotice, worker: Any) -> None:
    url = _link(_client(worker), notice.pk).data["url"]
    client = _client(None)

    assert _link(client, notice.pk).status_code == 401
    assert client.get(url).status_code == 401


def test_br_doc_006_link_of_another_staff_user_is_refused(
    notice: IncomeNotice, worker: Any
) -> None:
    url = _link(_client(worker), notice.pk).data["url"]

    response = _client(make_user("intake_worker")).get(url)

    assert response.status_code == 404
    assert response.data["code"] == "not_found"


class _SignerClock:
    """Stands in for the `time` module inside django.core.signing only."""

    def __init__(self, now: float) -> None:
        self.now = now

    def time(self) -> float:
        return self.now


@pytest.mark.parametrize(("age", "status"), [(299, 200), (300, 200), (301, 404)])
def test_br_doc_006_link_expires_after_five_minutes(
    notice: IncomeNotice,
    worker: Any,
    monkeypatch: pytest.MonkeyPatch,
    age: int,
    status: int,
) -> None:
    # Whole seconds on a controlled clock: the age at download is exactly `age`.
    clock = _SignerClock(float(int(timezone.now().timestamp())))
    monkeypatch.setattr(signing, "time", clock)
    client = _client(worker)
    url = _link(client, notice.pk).data["url"]

    clock.now += age

    assert client.get(url).status_code == status


def test_tampered_token_is_refused(notice: IncomeNotice, worker: Any) -> None:
    client = _client(worker)
    url = _link(client, notice.pk).data["url"]
    tampered = url[:-2] + ("A" if url[-2] != "A" else "B") + "/"

    assert client.get(tampered).status_code == 404


@pytest.mark.usefixtures("notice_rule")
def test_did_not_file_notice_has_no_link(worker: Any) -> None:
    notice = record_staff_notice(
        make_member().pk,
        {"did_not_file": True, "did_not_file_reason": "No income"},
        None,
        worker,
    )

    assert _link(_client(worker), notice.pk).status_code == 404


@pytest.mark.usefixtures("notice_rule")
def test_unknown_notice_has_no_link(worker: Any) -> None:
    assert _link(_client(worker), uuid4()).status_code == 404


def test_missing_blob_answers_404_and_logs_an_error(
    notice: IncomeNotice, worker: Any, caplog: pytest.LogCaptureFixture
) -> None:
    client = _client(worker)
    url = _link(client, notice.pk).data["url"]
    InMemoryFileStore.clear()

    with caplog.at_level("ERROR", logger="iris.documents"):
        response = client.get(url)

    assert response.status_code == 404
    errors = [
        getattr(r, "event", None) for r in caplog.records if r.levelname == "ERROR"
    ]
    assert "notice_file_missing" in errors


def test_storage_down_answers_503(notice: IncomeNotice, worker: Any) -> None:
    client = _client(worker)
    url = _link(client, notice.pk).data["url"]

    with override_settings(FILE_STORE_BACKEND=""):
        response = client.get(url)

    assert response.status_code == 503
    assert response.data["code"] == "storage_unavailable"


def test_superseded_notice_file_stays_available(
    notice: IncomeNotice, worker: Any
) -> None:
    _record(worker, member=notice.member, tax_year=2024, notice_date=date(2025, 5, 1))
    client = _client(worker)

    url = _link(client, notice.pk).data["url"]

    assert client.get(url).content == CONTENT


def test_errors_follow_the_request_language(notice: IncomeNotice, worker: Any) -> None:
    client = _client(worker)
    url = _link(client, notice.pk).data["url"]

    response = client.get(url[:-2] + "Z/", HTTP_ACCEPT_LANGUAGE="fr")

    assert response.status_code == 404
    assert response.data["message"] == "Ce lien de fichier est invalide ou expiré."
