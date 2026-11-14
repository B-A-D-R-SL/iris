# AI contribution: 50% or more AI-generated
"""POST /api/staff/households/{id}/approve/ (US-18).

approve_walk_in has its own tests (test_walk_in_approval.py); these check
access, the HTTP contract and that each outcome reaches the response.
"""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from django.apps import apps
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.documents.tests.factories import IncomeNoticeFactory
from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db
NOW = datetime(2026, 11, 8, 15, tzinfo=UTC)


def approve_url(household_id: object) -> str:
    """Approve route for one walk-in file."""
    return f"/api/staff/households/{household_id}/approve/"


@pytest.fixture(autouse=True)
def rules(monkeypatch: Any) -> None:
    """Rules approval reads, with a fixed clock (same as the service tests)."""
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    admin: Any = UserFactory(role="admin", password=None)
    for rule_type in ("auto_approval", "file_validity", "invitations"):
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
    """An intake worker."""
    return UserFactory(role="intake_worker", password=None)


@pytest.fixture
def staff_client(staff: Any) -> APIClient:
    """A client signed in as the intake worker."""
    client = APIClient()
    client.force_login(staff)
    return client


@pytest.fixture
def household(staff: Any) -> Any:
    """A complete, verified walk-in file, submitted, with the holder's notice."""
    household = HouseholdFactory(
        created_by=staff,
        status="submitted",
        submitted_at=NOW,
        identity_checked_in_person=True,
        verified_by=staff,
        verified_at=NOW,
        consent_data_processing_at=NOW,
        consent_text_version="2026-11-v1",
    )
    holder = MemberFactory(household=household, relation="holder")
    IncomeNoticeFactory(member=holder, recorded_by=staff)
    return household


def _notices(household: Any) -> Any:
    return apps.get_model("documents.IncomeNotice").objects.filter(
        member__household=household
    )


def test_eligible_file_is_approved(staff_client: APIClient, household: Any) -> None:
    """200 with the approval and its expiry."""
    response = staff_client.post(approve_url(household.pk))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(household.pk)
    assert body["status"] == "approved"
    assert body["status_reason"] == ""
    assert body["approved_at"].startswith("2026-11-08")
    assert body["expires_at"].startswith("2027-11-08")
    household.refresh_from_db()
    assert household.status == "approved"


def test_income_above_the_cut_off_is_rejected(
    staff_client: APIClient, household: Any
) -> None:
    """A rejection is a decision too: 200 with the reason code."""
    _notices(household).update(total_income_cents=3_000_001)

    body = staff_client.post(approve_url(household.pk)).json()

    assert body["status"] == "rejected"
    assert body["status_reason"] == "INCOME_ABOVE_LICO"
    assert body["approved_at"] is None


def test_a_notice_not_seen_in_person_sends_the_file_to_review(
    staff_client: APIClient, household: Any
) -> None:
    """Review reasons come back so staff can explain them."""
    _notices(household).update(seen_in_person=False)

    body = staff_client.post(approve_url(household.pk)).json()

    assert body["status"] == "review_required"
    assert body["status_reason"]


def test_an_incomplete_file_answers_400(
    staff_client: APIClient, household: Any
) -> None:
    """Missing address or consent stops the decision with a message."""
    type(household).objects.filter(pk=household.pk).update(street_name="")

    response = staff_client.post(approve_url(household.pk))

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    household.refresh_from_db()
    assert household.status == "submitted"


def test_a_decided_file_cannot_be_approved_again(
    staff_client: APIClient, household: Any
) -> None:
    """The second request answers 400 and changes nothing."""
    assert staff_client.post(approve_url(household.pk)).status_code == 200

    response = staff_client.post(approve_url(household.pk))

    assert response.status_code == 400


def test_unknown_file_answers_404(staff_client: APIClient) -> None:
    """A missing ID answers 404."""
    assert staff_client.post(approve_url(uuid4())).status_code == 404


def test_anonymous_requests_answer_401(household: Any) -> None:
    """Without a session nothing is decided."""
    assert APIClient().post(approve_url(household.pk)).status_code == 401


@pytest.mark.parametrize("role", ["beneficiary", "store_staff", "store_manager"])
def test_other_roles_get_403(household: Any, role: str) -> None:
    """Only intake workers and admins can decide a walk-in file."""
    store = StoreFactory() if role.startswith("store") else None
    client = APIClient()
    client.force_login(UserFactory(role=role, store=store))

    response = client.post(approve_url(household.pk))

    assert response.status_code == 403
    household.refresh_from_db()
    assert household.status == "submitted"


def test_admins_can_decide(household: Any) -> None:
    """Admins share the intake permission."""
    client = APIClient()
    client.force_login(UserFactory(role="admin"))

    assert client.post(approve_url(household.pk)).status_code == 200


# rule: BR-DUP-002
def test_a_draft_answers_400_until_it_is_submitted(
    staff_client: APIClient, household: Any
) -> None:
    Household.objects.filter(pk=household.pk).update(status="draft", submitted_at=None)

    response = staff_client.post(approve_url(household.pk))

    assert response.status_code == 400
    household.refresh_from_db()
    assert household.status == "draft"


def summary_url(household_id: object) -> str:
    """Decision summary route for one walk-in file."""
    return f"/api/staff/households/{household_id}/decision-summary/"


def test_the_summary_gives_size_income_and_threshold(
    staff_client: APIClient, household: Any
) -> None:
    """The numbers come from the API; nothing is saved by asking."""
    body = staff_client.get(summary_url(household.pk)).json()

    assert body == {
        "household_size": 1,
        "adult_count": 1,
        "total_income_cents": 1_234_500,
        "threshold_cents": 3_000_000,
        "ready_for_decision": True,
        "will_go_to_review": False,
        "eligible": True,
        "approved_months": 12,
        "valid_until": body["valid_until"],
    }
    # The same date approval would save (test_eligible_file_is_approved).
    assert body["valid_until"].startswith("2027-11-08")
    assert not apps.get_model("eligibility.EligibilityDecision").objects.exists()


def test_the_summary_says_when_the_file_will_go_to_review(
    staff_client: APIClient, household: Any
) -> None:
    _notices(household).update(seen_in_person=False)

    body = staff_client.get(summary_url(household.pk)).json()

    assert body["ready_for_decision"] is True
    assert body["will_go_to_review"] is True
    assert body["total_income_cents"] is None
    assert body["eligible"] is None


def test_the_summary_says_not_eligible_when_income_is_above_the_threshold(
    staff_client: APIClient, household: Any
) -> None:
    _notices(household).update(total_income_cents=3_000_001)

    body = staff_client.get(summary_url(household.pk)).json()

    assert body["will_go_to_review"] is False
    assert body["eligible"] is False
    # Approving would reject the file, so there is no validity to show.
    assert body["approved_months"] is None
    assert body["valid_until"] is None


def test_the_summary_is_not_ready_while_an_adult_has_no_notice(
    staff_client: APIClient, household: Any
) -> None:
    MemberFactory(household=household, relation="spouse_partner")

    body = staff_client.get(summary_url(household.pk)).json()

    assert body["adult_count"] == 2
    assert body["ready_for_decision"] is False


def test_the_summary_of_an_unknown_file_answers_404(staff_client: APIClient) -> None:
    assert staff_client.get(summary_url(uuid4())).status_code == 404


def test_the_summary_sends_a_submitted_file_with_a_missing_notice_to_review(
    staff_client: APIClient, household: Any
) -> None:
    """A member who turned 18 after submission cannot get a notice: review."""
    MemberFactory(household=household, relation="spouse_partner")

    body = staff_client.get(summary_url(household.pk)).json()

    assert body["ready_for_decision"] is True
    assert body["will_go_to_review"] is True


def test_the_decision_says_whether_an_invitation_was_not_sent(
    staff_client: APIClient, staff: Any, household: Any
) -> None:
    Household.objects.filter(pk=household.pk).update(email=staff.email)

    body = staff_client.post(approve_url(household.pk)).json()

    assert body["status"] == "approved"
    assert body["invitation_not_sent"] is True
