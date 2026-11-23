# AI contribution: 50% or more AI-generated
"""US-93: a walk-in invitation names its household and acceptance announces it."""

from collections.abc import Iterator
from hashlib import sha256
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from modules.accounts import services
from modules.accounts.models import Invitation, User
from modules.accounts.tests.factories import UserFactory
from modules.households.tests.factories import HouseholdFactory

pytestmark = pytest.mark.django_db
PASSWORD = "Uncommon-secret-9146!"


@pytest.fixture
def announced() -> Iterator[list[dict[str, Any]]]:
    """Record what acceptance sends, then disconnect the test receiver."""
    calls: list[dict[str, Any]] = []

    def receiver(sender: Any, **kwargs: Any) -> None:
        calls.append(kwargs)

    services.invitation_accepted.connect(receiver, weak=False, dispatch_uid="test")
    yield calls
    services.invitation_accepted.disconnect(dispatch_uid="test")


def test_invitation_stores_its_household(issue_invitation: Any) -> None:
    household: Any = HouseholdFactory()
    _, invitation = issue_invitation(household_id=household.pk)
    assert invitation.household_id == household.pk


def test_acceptance_sends_household_and_new_user(
    issue_invitation: Any, announced: list[dict[str, Any]]
) -> None:
    household: Any = HouseholdFactory()
    token, invitation = issue_invitation(household_id=household.pk)
    user = services.accept_invitation(token, PASSWORD)
    assert len(announced) == 1
    assert announced[0]["household_id"] == household.pk
    assert announced[0]["user"].pk == user.pk
    assert user.email == invitation.email


def test_acceptance_without_household_sends_nothing(
    issue_invitation: Any, announced: list[dict[str, Any]]
) -> None:
    token, _ = issue_invitation()
    services.accept_invitation(token, PASSWORD)
    assert announced == []


# rule: BR-HH-ACCOUNT-001
def test_receiver_failure_rolls_back_acceptance(issue_invitation: Any) -> None:
    household: Any = HouseholdFactory()
    token, invitation = issue_invitation(household_id=household.pk)

    def refuse(sender: Any, **kwargs: Any) -> None:
        raise ValidationError("refused", code="household_already_linked")

    services.invitation_accepted.connect(refuse, weak=False, dispatch_uid="refuse")
    try:
        with pytest.raises(ValidationError) as caught:
            services.accept_invitation(token, PASSWORD)
    finally:
        services.invitation_accepted.disconnect(dispatch_uid="refuse")
    assert caught.value.code == "household_already_linked"
    assert not User.objects.filter(email__iexact=invitation.email).exists()
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


def reissue(household: Any, email: str, invited_by: Any) -> str:
    return services.reissue_household_invitation(
        household_id=household.pk,
        email=email,
        first_name="Samira",
        last_name="Example",
        invited_by=invited_by,
    )


# rule: BR-HH-ACCOUNT-004
def test_reissue_expires_previous_household_links(
    issue_invitation: Any, invitation_clock: Any
) -> None:
    household: Any = HouseholdFactory()
    _, previous = issue_invitation(household_id=household.pk)
    token = reissue(household, previous.email, UserFactory(role="intake_worker"))
    previous.refresh_from_db()
    assert previous.expires_at == invitation_clock.now
    fresh = Invitation.objects.get(token_hash=sha256(token.encode()).hexdigest())
    assert fresh.household_id == household.pk
    assert fresh.role == "beneficiary"
    assert fresh.expires_at > invitation_clock.now


def test_reissue_expires_legacy_link_for_same_email(
    issue_invitation: Any, invitation_clock: Any
) -> None:
    """Links sent before invitations named their household (US-18)."""
    _, legacy = issue_invitation(email="holder@example.test")
    reissue(HouseholdFactory(), "holder@example.test", UserFactory(role="admin"))
    legacy.refresh_from_db()
    assert legacy.expires_at == invitation_clock.now


def test_reissue_leaves_other_households_links(
    issue_invitation: Any, invitation_clock: Any
) -> None:
    other: Any = HouseholdFactory()
    _, unrelated = issue_invitation(household_id=other.pk)
    reissue(HouseholdFactory(), "holder@example.test", UserFactory(role="admin"))
    unrelated.refresh_from_db()
    assert unrelated.expires_at > invitation_clock.now


def test_reissue_refuses_non_staff(issue_invitation: Any) -> None:
    with pytest.raises(PermissionDenied):
        reissue(HouseholdFactory(), "holder@example.test", UserFactory())
    assert not Invitation.objects.exists()


# rule: BR-HH-ACCOUNT-004
def test_resend_when_account_exists_keeps_previous_link(
    issue_invitation: Any, invitation_clock: Any
) -> None:
    household: Any = HouseholdFactory()
    _, previous = issue_invitation(household_id=household.pk)
    UserFactory(email=previous.email)
    with pytest.raises(ValidationError) as caught:
        reissue(household, previous.email, UserFactory(role="intake_worker"))
    assert caught.value.code == "email_already_registered"
    previous.refresh_from_db()
    assert previous.expires_at > invitation_clock.now
    assert Invitation.objects.count() == 1
