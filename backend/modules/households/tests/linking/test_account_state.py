# AI contribution: 50% or more AI-generated
"""US-93: what the staff screen is told about a file's account."""

from typing import Any

import pytest

from modules.households.account_link_queries import AccountLink, account_link
from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory
from modules.households.tests.linking.helpers import account, approved_walk_in

pytestmark = pytest.mark.django_db


def test_linked_file(staff: Any) -> None:
    household = approved_walk_in(staff, holder=account())
    assert account_link(household) == AccountLink("linked", "", None, None)


def test_draft_is_not_applicable(staff: Any) -> None:
    household = approved_walk_in(staff, status=Household.Status.DRAFT)
    assert account_link(household).status == "not_applicable"


def test_file_without_email(staff: Any) -> None:
    household = approved_walk_in(staff, email=None)
    assert account_link(household) == AccountLink("no_email", "", None, None)


def test_invited_when_no_account_uses_the_email(staff: Any) -> None:
    household = approved_walk_in(staff)
    assert account_link(household) == AccountLink("invited", "", None, None)


@pytest.mark.parametrize(
    ("make_account", "reason"),
    [
        (lambda: account("intake_worker"), "not_beneficiary"),
        (lambda: account("store_staff"), "not_beneficiary"),
        (lambda: account(is_active=False), "inactive"),
        (
            lambda: HouseholdFactory(
                holder=account(), channel="online", street_number="200"
            ),
            "has_household",
        ),
    ],
)
def test_cannot_link_says_why(staff: Any, make_account: Any, reason: str) -> None:
    household = approved_walk_in(staff)
    make_account()
    assert account_link(household) == AccountLink("cannot_link", reason, None, None)


def test_can_link_shows_the_name_on_the_account(staff: Any) -> None:
    household = approved_walk_in(staff)
    account(first_name="Sam", last_name="Exemple")
    assert account_link(household) == AccountLink("can_link", "", "Sam", "Exemple")
