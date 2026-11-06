# AI contribution: 50% or more AI-generated
"""queries.approved_household_id: the approval check for browsing (US-36)."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.queries import approved_household_id
from modules.households.tests.factories import HouseholdFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 6, 15, tzinfo=UTC)


def _online_file(holder: Any, **kwargs: Any) -> Household:
    values: dict[str, Any] = {
        "channel": Household.Channel.ONLINE,
        "holder": holder,
        "created_by": None,
        "status": Household.Status.APPROVED,
        "approved_at": NOW - timedelta(days=30),
        "expires_at": NOW + timedelta(days=335),
    }
    return cast(Household, HouseholdFactory(**(values | kwargs)))


@pytest.fixture
def holder() -> Any:
    return UserFactory(role="beneficiary")


def test_an_approved_file_that_has_not_expired_gives_its_id(holder: Any) -> None:
    household = _online_file(holder)
    assert approved_household_id(holder.pk, at=NOW) == household.pk


@pytest.mark.parametrize(
    "status",
    [status for status in Household.Status if status != Household.Status.APPROVED],
)
def test_any_other_status_gives_none(holder: Any, status: str) -> None:
    _online_file(holder, status=status)
    assert approved_household_id(holder.pk, at=NOW) is None


def test_a_file_expiring_exactly_now_is_no_longer_approved(holder: Any) -> None:
    _online_file(holder, expires_at=NOW)
    assert approved_household_id(holder.pk, at=NOW) is None


def test_an_expired_file_the_nightly_job_has_not_moved_yet_gives_none(
    holder: Any,
) -> None:
    _online_file(holder, expires_at=NOW - timedelta(hours=3))
    assert approved_household_id(holder.pk, at=NOW) is None


def test_an_approved_file_without_an_expiry_date_gives_none(holder: Any) -> None:
    _online_file(holder, expires_at=None)
    assert approved_household_id(holder.pk, at=NOW) is None


def test_a_user_without_a_household_gives_none(holder: Any) -> None:
    _online_file(UserFactory(role="beneficiary"))
    assert approved_household_id(holder.pk, at=NOW) is None
