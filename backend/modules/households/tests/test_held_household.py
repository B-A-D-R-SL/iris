# AI contribution: 50% or more AI-generated
"""queries.held_household_id: whose pickup history to show (US-48).

BR-RES-011: a beneficiary sees the history of the household they hold, whatever
its status. An anonymized file, or an account that holds none, gives None.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.queries import held_household_id
from modules.households.tests.factories import HouseholdFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 25, 15, tzinfo=UTC)


@pytest.fixture
def holder() -> Any:
    """A beneficiary account to hold the file."""
    return UserFactory(role="beneficiary")


def _online_file(holder: Any, **kwargs: Any) -> Household:
    """An online file held by ``holder``, approved unless overridden."""
    values: dict[str, Any] = {
        "channel": Household.Channel.ONLINE,
        "holder": holder,
        "created_by": None,
        "status": Household.Status.APPROVED,
        "approved_at": NOW - timedelta(days=30),
        "expires_at": NOW + timedelta(days=335),
    }
    return cast(Household, HouseholdFactory(**(values | kwargs)))


# rule: BR-RES-011
@pytest.mark.parametrize("status", Household.Status.values)
def test_every_status_gives_the_held_file(holder: Any, status: str) -> None:
    """Unlike browsing, the file's status does not matter."""
    household = _online_file(holder, status=status)

    assert held_household_id(holder.pk) == household.pk


# rule: BR-RES-011
def test_an_expired_file_gives_its_id(holder: Any) -> None:
    """An expired file is still the household's own file."""
    household = _online_file(holder, expires_at=NOW - timedelta(days=60))

    assert held_household_id(holder.pk) == household.pk


# rule: BR-RES-011
def test_an_anonymized_file_gives_none(holder: Any) -> None:
    """An anonymized file is no longer shown to its old account."""
    _online_file(holder, anonymized_at=NOW)

    assert held_household_id(holder.pk) is None


# rule: BR-RES-011
def test_a_user_without_a_household_gives_none(holder: Any) -> None:
    """Another account's file is never returned."""
    _online_file(UserFactory(role="beneficiary"))

    assert held_household_id(holder.pk) is None
