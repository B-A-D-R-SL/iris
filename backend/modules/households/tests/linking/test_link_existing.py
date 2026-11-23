# AI contribution: 50% or more AI-generated
"""US-93: staff link an existing beneficiary account at the counter."""

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import translation

from modules.households import account_link_queries
from modules.households.account_link_services import link_existing_account
from modules.households.models import Household
from modules.households.tests.approval.helpers import audit_events
from modules.households.tests.factories import HouseholdFactory
from modules.households.tests.linking.helpers import account, approved_walk_in

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def english() -> Iterator[None]:
    """Messages in English; French is the default and has its own test."""
    with translation.override("en"):
        yield


def refusal(household: Any, staff: Any) -> str:
    """The message staff see when the link is refused; the file stays unlinked."""
    with pytest.raises(ValidationError) as caught:
        link_existing_account(household.pk, staff)
    household.refresh_from_db()
    assert household.holder_id is None
    assert not audit_events(household).filter(action="link_account").exists()
    return str(caught.value.messages[0])


def test_staff_links_existing_beneficiary_account(staff: Any) -> None:
    household = approved_walk_in(staff)
    user = account()
    linked = link_existing_account(household.pk, staff)
    assert linked.holder_id == user.pk
    event = audit_events(household).get(action="link_account")
    assert (event.metadata, event.actor_id) == ({"method": "counter"}, staff.pk)


def test_refuses_unapproved_file(staff: Any) -> None:
    household = approved_walk_in(staff, status=Household.Status.SUBMITTED)
    account()
    assert refusal(household, staff) == (
        "Only an approved file can be linked to an account."
    )


def test_refuses_file_without_email(staff: Any) -> None:
    household = approved_walk_in(staff, email=None)
    assert refusal(household, staff) == (
        "This file has no email address. The household is served at the counter."
    )


def test_refuses_already_linked_file(staff: Any) -> None:
    household = approved_walk_in(staff)
    Household.objects.filter(pk=household.pk).update(
        holder=account(email="other@example.test")
    )
    account()
    with pytest.raises(ValidationError, match="already linked to an account"):
        link_existing_account(household.pk, staff)


def test_refuses_when_no_account(staff: Any) -> None:
    household = approved_walk_in(staff)
    assert refusal(household, staff) == (
        "No Iris account uses this file's email address."
    )


@pytest.mark.parametrize(
    "role", ["intake_worker", "admin", "store_staff", "store_manager"]
)
def test_refuses_staff_and_store_accounts(staff: Any, role: str) -> None:
    household = approved_walk_in(staff)
    account(role)
    assert refusal(household, staff) == (
        "Staff and store accounts cannot be linked to a household."
    )


def test_refuses_inactive_account(staff: Any) -> None:
    household = approved_walk_in(staff)
    account(is_active=False)
    assert refusal(household, staff) == (
        "This account is deactivated and cannot be linked."
    )


def test_refuses_account_holding_another_household(staff: Any) -> None:
    household = approved_walk_in(staff)
    HouseholdFactory(holder=account(), channel="online", street_number="200")
    assert refusal(household, staff) == (
        "This account is already linked to another household."
    )


def test_refuses_non_staff_actor(staff: Any) -> None:
    household = approved_walk_in(staff)
    user = account()
    with pytest.raises(PermissionDenied):
        link_existing_account(household.pk, user)


def test_refuses_unknown_or_online_file(staff: Any) -> None:
    online = approved_walk_in(staff, channel="online")
    account()
    with pytest.raises(Household.DoesNotExist):
        link_existing_account(online.pk, staff)


def test_refusal_messages_in_french(staff: Any) -> None:
    household = approved_walk_in(staff)
    with translation.override("fr"):
        assert refusal(household, staff) == (
            "Aucun compte Iris n'utilise le courriel de ce dossier."
        )


def test_concurrent_link_of_same_account_refuses_second(
    staff: Any, monkeypatch: Any
) -> None:
    """Another request linked the account after our checks: the column refuses."""
    household = approved_walk_in(staff)
    HouseholdFactory(holder=account(), channel="online", street_number="200")
    monkeypatch.setattr(account_link_queries, "holds_household", lambda _: False)
    assert refusal(household, staff) == (
        "This account is already linked to another household."
    )
