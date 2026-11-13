# AI contribution: 50% or more AI-generated
"""Queued invitation delivery checks the current token and assigned recipient."""

from datetime import timedelta

import pytest

from modules.accounts import queries
from modules.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_invitation_delivery_preflight_matches_recipient_without_consuming_token(
    issue_invitation,
):
    token, invitation = issue_invitation()
    assert queries.invitation_is_usable(token, invitation.email.upper())
    assert not queries.invitation_is_usable(token, "other@example.test")
    invitation.refresh_from_db()
    assert invitation.accepted_at is None


@pytest.mark.parametrize("token", ["", "invalid", "A" * 43, "A" * 43 + "\n", None])
def test_invitation_delivery_preflight_refuses_missing_or_invalid_tokens(token):
    assert not queries.invitation_is_usable(token, "recipient@example.test")


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(microseconds=1)])
def test_invitation_delivery_preflight_refuses_expiry_boundary_br_inv_001(
    issue_invitation, invitation_clock, offset
):
    token, invitation = issue_invitation()
    invitation_clock.now = invitation.expires_at + offset
    assert not queries.invitation_is_usable(token, invitation.email)


def test_invitation_delivery_preflight_refuses_consumed_token_br_inv_002(
    issue_invitation, invitation_clock
):
    token, invitation = issue_invitation()
    invitation.accepted_at = invitation_clock.now
    invitation.save(update_fields=["accepted_at"])
    assert not queries.invitation_is_usable(token, invitation.email)


@pytest.mark.parametrize("is_active", [True, False])
def test_invitation_delivery_preflight_refuses_registered_email_br_inv_003(
    issue_invitation, is_active
):
    token, invitation = issue_invitation()
    UserFactory(email=invitation.email, is_active=is_active)
    assert not queries.invitation_is_usable(token, invitation.email)
