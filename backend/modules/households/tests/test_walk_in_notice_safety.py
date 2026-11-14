# AI contribution: 50% or more AI-generated
"""Recording a walk-in notice: which files take one, and what the lock covers (T-03.18.2)."""

import threading
from copy import deepcopy
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection, transaction
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from adapters.file_store.memory import InMemoryFileStore
from modules.accounts.tests.factories import UserFactory
from modules.documents import services as document_services
from modules.documents.queries import current_notices
from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish

NON_FILER = {"did_not_file": "true", "did_not_file_reason": "No income in 2025"}
FILED = {
    "tax_year": "2025",
    "total_income_cents": "2345600",
    "name_on_notice": "Example Holder",
    "postal_code_on_notice": "H2X 1Y4",
    "notice_date": "2026-04-30",
    "seen_in_person": "true",
}


def _locked_elsewhere(household_id: Any) -> bool:
    """Whether another connection would wait for this household's row lock."""
    outcome: list[bool] = []

    def probe() -> None:
        try:
            with transaction.atomic():
                Household.objects.select_for_update(nowait=True).get(pk=household_id)
            outcome.append(False)
        except DatabaseError:
            outcome.append(True)
        finally:
            connection.close()

    thread = threading.Thread(target=probe)
    thread.start()
    thread.join(timeout=10)
    return outcome[0]


class LockProbeStore(InMemoryFileStore):
    """The test file store; it notes whether the household was locked during upload."""

    def __init__(self, household_id: Any) -> None:
        self.household_id = household_id
        self.locked_during_upload: list[bool] = []

    def put(self, content: bytes, *, content_type: str, prefix: str) -> str:
        self.locked_during_upload.append(_locked_elsewhere(self.household_id))
        return super().put(content, content_type=content_type, prefix=prefix)


@pytest.fixture
def worker() -> Any:
    admin: Any = UserFactory(role="admin")
    publish("notice_upload", deepcopy(DEFAULT_RULE_VALUES["notice_upload"]), admin)
    return UserFactory(role="intake_worker")


@pytest.fixture
def holder() -> Any:
    household = HouseholdFactory()
    return MemberFactory(
        household=household, relation="holder", date_of_birth="1990-01-01"
    )


def _post(worker: Any, member: Any, data: dict[str, Any]) -> Any:
    client = APIClient()
    client.force_authenticate(user=worker)
    url = reverse("staff-households-notices", kwargs={"id": member.household_id})
    return client.post(url, {"member": str(member.pk), **data}, format="multipart")


@pytest.mark.django_db
def test_an_anonymized_draft_takes_no_notice(holder: Any, worker: Any) -> None:
    """Like every other walk-in path, an anonymized file is not found."""
    Household.objects.filter(pk=holder.household_id).update(
        anonymized_at=timezone.now()
    )

    response = _post(worker, holder, NON_FILER)

    assert response.status_code == 404
    assert not current_notices([holder.pk])


@pytest.mark.django_db(transaction=True)
def test_the_file_is_stored_before_the_household_is_locked(
    holder: Any, worker: Any, monkeypatch: Any
) -> None:
    """A slow upload must not hold the row that draft edits and approval wait on."""
    store = LockProbeStore(holder.household_id)
    monkeypatch.setattr(document_services, "_file_store", lambda: store)
    scan = SimpleUploadedFile("scan.pdf", b"%PDF-1.7 walk-in", "application/pdf")

    response = _post(worker, holder, {**FILED, "file": scan})

    assert response.status_code == 201, response.data
    assert store.locked_during_upload == [False]
    assert current_notices([holder.pk])[holder.pk].file_ref


@pytest.mark.django_db
def test_a_refused_member_stores_no_file(
    holder: Any, worker: Any, monkeypatch: Any
) -> None:
    """The draft and member are checked before anything is uploaded."""
    child = MemberFactory(household=holder.household, date_of_birth="2016-03-01")
    store = LockProbeStore(holder.household_id)
    monkeypatch.setattr(document_services, "_file_store", lambda: store)
    scan = SimpleUploadedFile("scan.pdf", b"%PDF-1.7 walk-in", "application/pdf")

    response = _post(worker, child, {**FILED, "file": scan})

    assert response.status_code == 400
    assert store.locked_during_upload == []


@pytest.mark.django_db
def test_a_file_submitted_during_the_upload_keeps_no_notice_or_file(
    holder: Any, worker: Any, monkeypatch: Any
) -> None:
    """The draft is checked again under the lock; the stored file is then removed."""
    InMemoryFileStore.clear()
    monkeypatch.setattr(document_services, "_file_store", InMemoryFileStore)
    prepare = document_services.prepare_staff_notice

    def prepare_while_submitted_elsewhere(*args: Any, **kwargs: Any) -> Any:
        prepared = prepare(*args, **kwargs)
        Household.objects.filter(pk=holder.household_id).update(status="submitted")
        return prepared

    monkeypatch.setattr(
        document_services, "prepare_staff_notice", prepare_while_submitted_elsewhere
    )
    scan = SimpleUploadedFile("scan.pdf", b"%PDF-1.7 walk-in", "application/pdf")

    response = _post(worker, holder, {**FILED, "file": scan})

    assert response.status_code == 400
    assert "status" in response.data["fields"]
    assert InMemoryFileStore.references() == []
    assert not current_notices([holder.pk])
