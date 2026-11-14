# AI contribution: 50% or more AI-generated
"""lock_approved_household (US-41): who may reserve, read under a row lock."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.db import transaction

from modules.accounts.tests.factories import UserFactory
from modules.households.services import lock_approved_household
from modules.households.tests.factories import HouseholdFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 9, 15, tzinfo=UTC)


def _household(**kwargs: Any) -> Any:
    values: dict[str, Any] = {
        "channel": "online",
        "holder": UserFactory(role="beneficiary"),
        "created_by": None,
        "status": "approved",
        "approved_at": NOW - timedelta(days=30),
        "expires_at": NOW + timedelta(days=335),
    }
    return HouseholdFactory(**(values | kwargs))


def _locked(household_id: Any) -> bool:
    with transaction.atomic():
        return lock_approved_household(household_id, at=NOW)


# rule: BR-RES-006
def test_approved_household_may_reserve() -> None:
    assert _locked(_household().pk) is True


# rule: BR-RES-006
@pytest.mark.parametrize(
    "status",
    [
        "draft",
        "submitted",
        "review_required",
        "awaiting_visit",
        "renewal_needed",
        "suspended",
        "rejected",
    ],
)
def test_other_statuses_may_not_reserve(status: str) -> None:
    assert _locked(_household(status=status).pk) is False


# rule: BR-RES-006 expiry is checked even before the nightly job runs.
def test_expired_approved_household_may_not_reserve() -> None:
    assert _locked(_household(expires_at=NOW).pk) is False
    assert _locked(_household(expires_at=NOW + timedelta(seconds=1)).pk) is True


def test_unknown_household_may_not_reserve() -> None:
    assert _locked(uuid.uuid4()) is False


# Ordinary tests already run inside a transaction, so this one must not.
@pytest.mark.django_db(transaction=True)
def test_lock_must_be_taken_inside_a_transaction() -> None:
    with pytest.raises(RuntimeError, match="transaction"):
        lock_approved_household(_household().pk, at=NOW)
