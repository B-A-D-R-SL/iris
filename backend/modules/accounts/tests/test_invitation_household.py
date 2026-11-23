# AI contribution: 50% or more AI-generated
"""US-93: a walk-in invitation names its household and acceptance announces it."""

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.exceptions import ValidationError

from modules.accounts import services
from modules.accounts.models import User
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
    household = HouseholdFactory()
    _, invitation = issue_invitation(household_id=household.pk)
    assert invitation.household_id == household.pk


def test_acceptance_sends_household_and_new_user(
    issue_invitation: Any, announced: list[dict[str, Any]]
) -> None:
    household = HouseholdFactory()
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


def test_receiver_failure_rolls_back_acceptance(issue_invitation: Any) -> None:
    household = HouseholdFactory()
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
