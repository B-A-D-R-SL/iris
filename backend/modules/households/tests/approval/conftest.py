# AI contribution: 50% or more AI-generated
"""Rules on a fixed clock, staff, a ready walk-in and the email queue (US-18)."""

from copy import deepcopy
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.documents.tests.factories import IncomeNoticeFactory
from modules.households.tests.approval.helpers import NOW
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.notifications.tasks import send_email
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish


@pytest.fixture(autouse=True)
def rules(monkeypatch: Any) -> None:
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    admin: Any = UserFactory(role="admin", password=None)
    for rule_type in (
        "auto_approval",
        "file_validity",
        "household_size",
        "invitations",
    ):
        publish(
            rule_type,
            deepcopy(DEFAULT_RULE_VALUES[rule_type]),
            admin,
            effective_from=NOW - timedelta(days=1),
        )
    publish(
        "lico_thresholds",
        {
            "year": 2025,
            "source_url": "https://www.statcan.gc.ca/",
            "retrieved_on": "2026-10-01",
            "thresholds": {str(size): 3_000_000 * size for size in range(1, 8)},
        },
        admin,
        effective_from=NOW - timedelta(days=1),
    )


@pytest.fixture
def staff() -> Any:
    return UserFactory(role="intake_worker", password=None)


@pytest.fixture
def household(staff: Any) -> Any:
    household = HouseholdFactory(
        created_by=staff,
        identity_checked_in_person=True,
        verified_by=staff,
        verified_at=NOW,
        consent_data_processing_at=NOW,
        consent_text_version="2026-11-v1",
    )
    holder = MemberFactory(household=household, relation="holder")
    IncomeNoticeFactory(member=holder, recorded_by=staff)
    return household


@pytest.fixture
def email_jobs(monkeypatch: Any) -> list[dict[str, Any]]:
    """Capture the post-commit queue arguments without running a worker."""
    queued: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: queued.append(kwargs))
    return queued
