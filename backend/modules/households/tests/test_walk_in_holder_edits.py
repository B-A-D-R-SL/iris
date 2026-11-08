# AI contribution: 50% or more AI-generated
"""PATCH /api/staff/households/{id}/ on the holder after their notice is recorded.

The holder keeps one member row, so a corrected name or date of birth stays on
the same person and their notice stays current. The notice keeps the name it
was recorded with, so a later check can still compare the two.
"""

from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.documents.queries import current_notices
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish

pytestmark = pytest.mark.django_db

HOLDER = {
    "first_name": "Example",
    "last_name": "Holder",
    "date_of_birth": "1990-01-01",
    "phone": "(514) 555-0101",
}


@pytest.fixture
def worker() -> Any:
    return UserFactory(role="intake_worker")


@pytest.fixture
def holder() -> Any:
    return MemberFactory(
        household=HouseholdFactory(phone="+15145550101"),
        relation="holder",
        first_name="Example",
        last_name="Holder",
        date_of_birth="1990-01-01",
    )


@pytest.fixture
def notice(holder: Any, worker: Any) -> Any:
    """A filed notice for the holder, recorded through the staff endpoint."""
    admin: Any = UserFactory(role="admin")
    publish(
        "notice_upload",
        deepcopy(DEFAULT_RULE_VALUES["notice_upload"]),
        admin,
        effective_from=datetime(2020, 1, 1, tzinfo=UTC),
    )
    data = {
        "member": str(holder.pk),
        "file": SimpleUploadedFile(
            "scan.pdf", b"%PDF-1.7 holder", content_type="application/pdf"
        ),
        "tax_year": "2025",
        "total_income_cents": "2345600",
        "name_on_notice": "Example Holder",
        "postal_code_on_notice": "H2X 1Y4",
        "notice_date": "2026-04-30",
        "seen_in_person": "true",
    }
    url = reverse("staff-households-notices", kwargs={"id": holder.household_id})
    response = _client(worker).post(url, data, format="multipart")
    assert response.status_code == 201, response.data
    return current_notices([holder.pk])[holder.pk]


def _client(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _patch_holder(worker: Any, holder: Any, values: dict[str, str]) -> Any:
    url = reverse("staff-households-detail", kwargs={"id": holder.household_id})
    return _client(worker).patch(url, {"holder": values}, format="json")


def test_correcting_the_holders_name_and_birth_date_keeps_their_notice(
    holder: Any, worker: Any, notice: Any
) -> None:
    corrected = HOLDER | {
        "first_name": "Exemple",
        "last_name": "Titulaire",
        "date_of_birth": "1990-01-02",
    }

    response = _patch_holder(worker, holder, corrected)

    assert response.status_code == 200, response.data
    holder.refresh_from_db()
    assert (holder.first_name, holder.last_name) == ("Exemple", "Titulaire")
    assert holder.date_of_birth == date(1990, 1, 2)
    current = current_notices([holder.pk])[holder.pk]
    assert current.pk == notice.pk
    assert current.name_on_notice == "Example Holder"


def test_resending_the_holder_with_a_new_phone_keeps_their_notice(
    holder: Any, worker: Any, notice: Any
) -> None:
    response = _patch_holder(worker, holder, HOLDER | {"phone": "(514) 555-0199"})

    assert response.status_code == 200, response.data
    holder.household.refresh_from_db()
    assert holder.household.phone == "+15145550199"
    holder.refresh_from_db()
    assert (holder.first_name, holder.last_name) == ("Example", "Holder")
    assert current_notices([holder.pk])[holder.pk].pk == notice.pk
