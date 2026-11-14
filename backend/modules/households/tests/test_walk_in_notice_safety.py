# AI contribution: 50% or more AI-generated
"""Recording a walk-in notice: which files take one, and what the lock covers (T-03.18.2)."""

from copy import deepcopy
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.documents.queries import current_notices
from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish

NON_FILER = {"did_not_file": "true", "did_not_file_reason": "No income in 2025"}


@pytest.fixture
def worker(db: Any) -> Any:
    admin: Any = UserFactory(role="admin")
    publish("notice_upload", deepcopy(DEFAULT_RULE_VALUES["notice_upload"]), admin)
    return UserFactory(role="intake_worker")


@pytest.fixture
def holder(db: Any) -> Any:
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
