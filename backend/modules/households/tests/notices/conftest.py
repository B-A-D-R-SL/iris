# AI contribution: 50% or more AI-generated
"""The notice rule, an intake worker and a walk-in with a holder and a child."""

from typing import Any

import pytest

from modules.accounts.tests.factories import UserFactory
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.households.tests.notices.helpers import publish_notice_rule


@pytest.fixture(autouse=True)
def _notice_rule() -> None:
    publish_notice_rule()


@pytest.fixture
def worker() -> Any:
    return UserFactory(role="intake_worker")


@pytest.fixture
def household() -> Any:
    return HouseholdFactory(consented=True)


@pytest.fixture
def holder(household: Any) -> Any:
    return MemberFactory(
        household=household, relation="holder", date_of_birth="1990-01-01"
    )


@pytest.fixture
def child(household: Any) -> Any:
    return MemberFactory(
        household=household, relation="child", date_of_birth="2016-03-01"
    )
