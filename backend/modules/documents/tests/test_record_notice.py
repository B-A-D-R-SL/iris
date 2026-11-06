# AI contribution: 50% or more AI-generated
"""record_staff_notice: saving, superseding, storage and failures (T-03.18.2, #467)."""

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from adapters.file_store.base import FileStoreUnavailable, StoredFile
from adapters.file_store.memory import InMemoryFileStore
from modules.documents.models import IncomeNotice
from modules.documents.queries import current_notices
from modules.documents.services import NoticeServiceUnavailable, record_staff_notice
from modules.documents.tests.factories import make_member, make_user

pytestmark = pytest.mark.django_db

CONTENT = b"%PDF-1.7 test"


def _pdf(content: bytes = CONTENT) -> SimpleUploadedFile:
    return SimpleUploadedFile("scan.pdf", content, content_type="application/pdf")


def _filed(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "did_not_file": False,
        "tax_year": 2025,
        "total_income_cents": 4_321_000,
        "name_on_notice": "Example Holder",
        "postal_code_on_notice": "H2X 1Y4",
        "notice_date": date(2026, 4, 30),
        "seen_in_person": True,
    }
    return values | changes


DID_NOT_FILE = {"did_not_file": True, "did_not_file_reason": "No income in 2025"}


@pytest.fixture
def member() -> Any:
    return make_member()


class BrokenStore:
    def put(self, content: bytes, *, content_type: str, prefix: str) -> str:
        raise FileStoreUnavailable("down")

    def read(self, reference: str) -> StoredFile:
        raise FileStoreUnavailable("down")

    def delete(self, reference: str) -> None:
        raise FileStoreUnavailable("down")


@pytest.mark.usefixtures("notice_rule")
def test_br_doc_001_filed_notice_is_saved_with_staff_source(
    member: Any, worker: Any
) -> None:
    notice = record_staff_notice(member.pk, _filed(), _pdf(), worker)

    notice.refresh_from_db()
    assert notice.member_id == member.pk
    assert notice.status == IncomeNotice.Status.CONFIRMED
    assert notice.source == IncomeNotice.Source.STAFF
    assert notice.recorded_by == worker
    assert (notice.tax_year, notice.total_income_cents) == (2025, 4_321_000)
    assert notice.name_on_notice == "Example Holder"
    assert notice.postal_code_on_notice == "H2X 1Y4"
    assert notice.notice_date == date(2026, 4, 30)
    assert notice.seen_in_person is True
    assert notice.file_ref.startswith("income-notices/")
    assert InMemoryFileStore().read(notice.file_ref) == StoredFile(
        CONTENT, "application/pdf"
    )


@pytest.mark.usefixtures("notice_rule")
def test_br_doc_003_did_not_file_is_saved_without_a_file(
    member: Any, worker: Any
) -> None:
    notice = record_staff_notice(member.pk, DID_NOT_FILE, None, worker)

    notice.refresh_from_db()
    assert notice.status == IncomeNotice.Status.DID_NOT_FILE
    assert notice.did_not_file_reason == "No income in 2025"
    assert notice.file_ref == ""
    assert notice.seen_in_person is False
    assert InMemoryFileStore.references() == []


@pytest.mark.usefixtures("notice_rule")
def test_br_doc_005_new_entry_supersedes_and_keeps_history(
    member: Any, worker: Any
) -> None:
    first = record_staff_notice(member.pk, _filed(), _pdf(), worker)
    second = record_staff_notice(member.pk, DID_NOT_FILE, None, worker)

    first.refresh_from_db()
    assert first.superseded_at is not None
    assert IncomeNotice.objects.filter(member_id=member.pk).count() == 2
    assert InMemoryFileStore().read(first.file_ref).content == CONTENT
    assert current_notices([member.pk]) == {member.pk: second}


def test_br_doc_004_limit_comes_from_the_rule(
    publish_notice_rule: Callable[..., None], member: Any, worker: Any
) -> None:
    publish_notice_rule()
    publish_notice_rule(max_bytes=8)

    with pytest.raises(ValidationError) as caught:
        record_staff_notice(member.pk, _filed(), _pdf(b"%PDF-1.7 "), worker)

    assert set(caught.value.message_dict) == {"file"}
    assert not IncomeNotice.objects.exists()
    assert InMemoryFileStore.references() == []


@pytest.mark.usefixtures("notice_rule")
def test_rule_errors_are_field_errors(member: Any, worker: Any) -> None:
    with pytest.raises(ValidationError) as caught:
        record_staff_notice(member.pk, _filed(tax_year=None), _pdf(), worker)

    assert set(caught.value.message_dict) == {"tax_year"}
    assert InMemoryFileStore.references() == []


def test_missing_rule_fails_closed(member: Any, worker: Any) -> None:
    with pytest.raises(NoticeServiceUnavailable):
        record_staff_notice(member.pk, _filed(), _pdf(), worker)

    assert not IncomeNotice.objects.exists()


@pytest.mark.usefixtures("notice_rule")
@override_settings(FILE_STORE_BACKEND="")
def test_unconfigured_storage_fails_closed(member: Any, worker: Any) -> None:
    with pytest.raises(NoticeServiceUnavailable):
        record_staff_notice(member.pk, _filed(), _pdf(), worker)

    assert not IncomeNotice.objects.exists()


@pytest.mark.usefixtures("notice_rule")
def test_storage_failure_leaves_no_row(member: Any, worker: Any) -> None:
    with pytest.raises(NoticeServiceUnavailable):
        record_staff_notice(
            member.pk, _filed(), _pdf(), worker, file_store=BrokenStore()
        )

    assert not IncomeNotice.objects.exists()


@pytest.mark.usefixtures("notice_rule")
def test_database_failure_after_upload_deletes_the_file(
    member: Any, worker: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(self: IncomeNotice, *args: Any, **kwargs: Any) -> None:
        raise ValidationError({"member": "refused"})

    monkeypatch.setattr(IncomeNotice, "full_clean", refuse)

    with pytest.raises(ValidationError):
        record_staff_notice(member.pk, _filed(), _pdf(), worker)

    assert InMemoryFileStore.references() == []


@pytest.mark.usefixtures("notice_rule")
@pytest.mark.parametrize(
    ("role", "active"),
    [
        ("beneficiary", True),
        ("store_staff", True),
        ("store_manager", True),
        ("intake_worker", False),
    ],
)
def test_non_staff_is_refused(member: Any, role: str, active: bool) -> None:
    user = make_user(role, active=active)

    with pytest.raises(PermissionDenied):
        record_staff_notice(member.pk, _filed(), _pdf(), user)

    assert not IncomeNotice.objects.exists()
    assert InMemoryFileStore.references() == []


@pytest.mark.usefixtures("notice_rule")
def test_logs_carry_no_personal_values(
    member: Any, worker: Any, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="iris.documents"):
        record_staff_notice(member.pk, _filed(), _pdf(), worker)
        record_staff_notice(member.pk, DID_NOT_FILE, None, worker)

    events = [
        getattr(r, "event", None) for r in caplog.records if r.name == "iris.documents"
    ]
    assert events == ["notice_recorded", "notice_superseded", "notice_recorded"]
    for secret in ("4321000", "43210", "Example Holder", "H2X 1Y4", "scan.pdf"):
        assert secret not in caplog.text
    assert "No income" not in caplog.text


class UndeletableStore(InMemoryFileStore):
    def delete(self, reference: str) -> None:
        raise FileStoreUnavailable("down")


@pytest.mark.usefixtures("notice_rule")
def test_cleanup_failure_is_logged_and_the_database_error_kept(
    member: Any,
    worker: Any,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def refuse(self: IncomeNotice, *args: Any, **kwargs: Any) -> None:
        raise ValidationError({"member": "refused"})

    monkeypatch.setattr(IncomeNotice, "full_clean", refuse)

    with (
        caplog.at_level("ERROR", logger="iris.documents"),
        pytest.raises(ValidationError),
    ):
        record_staff_notice(
            member.pk, _filed(), _pdf(), worker, file_store=UndeletableStore()
        )

    events = [getattr(r, "event", None) for r in caplog.records]
    assert "notice_file_cleanup_failed" in events
