# AI contribution: 50% or more AI-generated
"""US-93: staff resend the walk-in set-password invitation."""

import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import translation

from iris.observability import JsonLogFormatter
from modules.accounts import services as account_services
from modules.households.account_link_services import resend_invitation
from modules.households.models import Household
from modules.households.tests.approval.helpers import audit_events, invitations
from modules.households.tests.linking.conftest import emailed_token
from modules.households.tests.linking.helpers import (
    HOLDER_EMAIL,
    PASSWORD,
    account,
    approved_walk_in,
)

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]


@pytest.fixture(autouse=True)
def english(settings: Any) -> Iterator[None]:
    settings.PUBLIC_APP_ORIGIN = "https://iris.example.test"
    with translation.override("en"):
        yield


# rule: BR-HH-ACCOUNT-004
def test_previous_link_stops_working_after_resend(
    household: Any,
    staff: Any,
    invitation_token: str,
    email_jobs: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        resend_invitation(household.pk, staff)
    new_token = emailed_token(email_jobs[-1])
    with pytest.raises(ValidationError) as caught:
        account_services.accept_invitation(invitation_token, PASSWORD)
    assert caught.value.code == "invitation_expired"
    user = account_services.accept_invitation(new_token, PASSWORD)
    household.refresh_from_db()
    assert household.holder_id == user.pk


def test_resend_queues_email_after_commit(
    staff: Any,
    email_jobs: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
) -> None:
    household = approved_walk_in(staff)
    with django_capture_on_commit_callbacks(execute=True):
        resend_invitation(household.pk, staff)
        assert email_jobs == []
    assert len(email_jobs) == 1
    assert invitations().get().household_id == household.pk


# rule: BR-HH-ACCOUNT-004
@pytest.mark.parametrize(
    ("change", "message"),
    [
        (
            {"status": Household.Status.SUBMITTED},
            "Only an approved file can be linked to an account.",
        ),
        (
            {"email": None},
            "This file has no email address. The household is served at the counter.",
        ),
        ("linked", "This file is already linked to an account."),
    ],
)
def test_resend_refuses_unapproved_linked_or_emailless_file(
    staff: Any, email_jobs: list[dict[str, Any]], change: Any, message: str
) -> None:
    if change == "linked":
        household = approved_walk_in(staff, holder=account(email="o@example.test"))
    else:
        household = approved_walk_in(staff, **change)
    with pytest.raises(ValidationError) as caught:
        resend_invitation(household.pk, staff)
    assert caught.value.messages == [message]
    assert not invitations().exists()
    assert email_jobs == []


# rule: BR-HH-ACCOUNT-004
def test_resend_when_account_exists_says_link_it(staff: Any) -> None:
    household = approved_walk_in(staff)
    account()
    with pytest.raises(ValidationError) as caught:
        resend_invitation(household.pk, staff)
    assert caught.value.messages == [
        (
            "This email address already has an Iris account. "
            "Link that account instead of sending an invitation."
        )
    ]


def test_resend_refuses_non_staff(staff: Any) -> None:
    household = approved_walk_in(staff)
    with pytest.raises(PermissionDenied):
        resend_invitation(household.pk, account(email="other@example.test"))


def test_resend_audit_and_log(
    staff: Any, caplog: Any, django_capture_on_commit_callbacks: Any
) -> None:
    household = approved_walk_in(staff)
    with (
        caplog.at_level(logging.INFO, logger="iris.households"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        resend_invitation(household.pk, staff)
    event = audit_events(household).get(action="invite")
    assert (event.actor_id, event.metadata) == (staff.pk, {})
    [record] = [
        r for r in caplog.records if r.getMessage() == "walk_in_invitation_resent"
    ]
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload["household_id"] == str(household.pk)
    assert HOLDER_EMAIL not in json.dumps(payload)
