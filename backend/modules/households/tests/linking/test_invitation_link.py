# AI contribution: 50% or more AI-generated
"""US-93: accepting the walk-in set-password invitation links the account."""

import json
import logging
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import translation
from rest_framework.test import APIClient

from iris.observability import JsonLogFormatter
from modules.accounts import services as account_services
from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.tests.approval.helpers import (
    audit_events,
    invitations,
    submit_and_approve,
)
from modules.households.tests.linking.conftest import HOLDER_EMAIL, PASSWORD

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]


def test_accepting_walk_in_invitation_links_holder(
    household: Any, invitation_token: str
) -> None:
    user = account_services.accept_invitation(invitation_token, PASSWORD)
    household.refresh_from_db()
    assert household.holder_id == user.pk
    event = audit_events(household).get(action="link_account")
    assert event.metadata == {"method": "invitation"}
    assert event.actor_id == user.pk


def test_walk_in_with_holder_passes_model_validation(household: Any) -> None:
    household.holder = UserFactory(role="beneficiary")
    household.full_clean()


def test_accept_for_already_linked_household_rolls_back(
    household: Any, invitation_token: str
) -> None:
    other: Any = UserFactory(role="beneficiary")
    Household.objects.filter(pk=household.pk).update(holder=other)
    with pytest.raises(ValidationError) as caught:
        account_services.accept_invitation(invitation_token, PASSWORD)
    assert caught.value.code == "household_already_linked"
    assert not get_user_model().objects.filter(email=HOLDER_EMAIL).exists()
    assert invitations().get().accepted_at is None
    household.refresh_from_db()
    assert household.holder_id == other.pk


def test_accept_for_anonymized_household_is_invalid(
    household: Any, invitation_token: str
) -> None:
    Household.objects.filter(pk=household.pk).update(anonymized_at=household.created_at)
    with pytest.raises(ValidationError) as caught:
        account_services.accept_invitation(invitation_token, PASSWORD)
    assert caught.value.code == "invitation_invalid"
    assert not get_user_model().objects.filter(email=HOLDER_EMAIL).exists()


def test_walk_in_without_email_is_approved_without_invitation(
    household: Any, staff: Any, email_jobs: list[dict[str, Any]]
) -> None:
    """AC: a counter-only file still works; an account stays optional."""
    submit_and_approve(household, staff)
    household.refresh_from_db()
    assert household.status == Household.Status.APPROVED
    assert household.holder_id is None
    assert not invitations().exists()
    assert email_jobs == []


def test_link_logs_only_household_id(
    household: Any,
    invitation_token: str,
    caplog: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    with (
        caplog.at_level(logging.INFO, logger="iris.households"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        account_services.accept_invitation(invitation_token, PASSWORD)
    [record] = [r for r in caplog.records if r.getMessage() == "walk_in_account_linked"]
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload["event"] == "walk_in_account_linked"
    assert payload["household_id"] == str(household.pk)
    assert HOLDER_EMAIL not in json.dumps(payload)


def test_accept_api_reports_household_already_linked(
    household: Any, invitation_token: str
) -> None:
    Household.objects.filter(pk=household.pk).update(
        holder=UserFactory(role="beneficiary")
    )
    response = APIClient().post(
        "/api/invitations/accept/",
        {"token": invitation_token, "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "household_already_linked"
    with translation.override("fr"):
        assert body["message"] == str(
            translation.gettext(
                "This household file is already linked to another account. "
                "Ask the food bank staff for help."
            )
        )
    assert body["message"].startswith("Ce dossier")
