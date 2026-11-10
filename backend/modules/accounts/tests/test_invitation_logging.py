# AI contribution: 50% or more AI-generated
"""Invitation success events follow commits and contain no recipient or secret data."""

import logging
from hashlib import sha256

import pytest
from django.db import transaction

from modules.accounts import services
from modules.accounts.models import Invitation, User
from modules.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
PASSWORD = "logging-test-invitation-657"


@pytest.fixture
def invitation_logs(caplog, monkeypatch):
    """Capture account events without relying on the application's root handlers."""
    logger = logging.getLogger("iris.accounts")
    monkeypatch.setattr(logger, "propagate", False)
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger=logger.name):
            yield caplog
    finally:
        logger.removeHandler(caplog.handler)


def _assert_private_event(record, event, sensitive_values):
    """Inspect the raw record so formatter filtering cannot hide leaked extras."""
    assert record.name == "iris.accounts"
    assert record.levelno == logging.INFO
    assert record.getMessage() == event
    assert record.event == event
    assert record.args == ()
    assert record.exc_info is None
    assert record.stack_info is None
    standard_fields = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
    assert set(vars(record)) - standard_fields == {"event"}
    for value in sensitive_values:
        assert str(value) not in str(vars(record))


def test_creation_logs_private_success_only_after_commit(
    invitation_rule,
    invitation_values,
    invitation_logs,
    django_capture_on_commit_callbacks,
):
    """Creation emits exactly one event after the outer transaction commits."""
    inviter = UserFactory(role=User.Role.ADMIN)
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with transaction.atomic():
            token = services.create_invitation(
                **{**invitation_values, "invited_by": inviter}
            )
            invitation = Invitation.objects.get(email=invitation_values["email"])
            assert invitation_logs.records == []
        assert invitation_logs.records == []

    assert len(callbacks) == 1
    assert len(invitation_logs.records) == 1
    _assert_private_event(
        invitation_logs.records[0],
        "invitation_created",
        [
            token,
            invitation.token_hash,
            invitation.email,
            invitation.first_name,
            invitation.last_name,
            invitation.pk,
            inviter.pk,
            PASSWORD,
        ],
    )


def test_rolled_back_creation_logs_no_success(
    invitation_rule,
    invitation_values,
    invitation_logs,
    django_capture_on_commit_callbacks,
):
    """A caller rollback removes the invitation and discards its queued event."""
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.create_invitation(**invitation_values)
        assert invitation_logs.records == []
        raise RuntimeError("caller rolled back")

    assert callbacks == []
    assert invitation_logs.records == []
    assert not Invitation.objects.filter(email=invitation_values["email"]).exists()


def test_acceptance_logs_private_success_only_after_commit(
    issue_invitation, invitation_logs, django_capture_on_commit_callbacks
):
    """Accepting an invitation emits only its event after the outer commit."""
    token, invitation = issue_invitation()
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with transaction.atomic():
            user = services.accept_invitation(token, PASSWORD)
            invitation.refresh_from_db()
            assert invitation.accepted_at is not None
            assert invitation_logs.records == []
        assert invitation_logs.records == []

    assert len(callbacks) == 1
    assert len(invitation_logs.records) == 1
    _assert_private_event(
        invitation_logs.records[0],
        "invitation_accepted",
        [
            token,
            sha256(token.encode("utf-8")).hexdigest(),
            PASSWORD,
            user.password,
            invitation.email,
            invitation.first_name,
            invitation.last_name,
            invitation.pk,
            user.pk,
        ],
    )


def test_rolled_back_acceptance_logs_no_success(
    issue_invitation, invitation_logs, django_capture_on_commit_callbacks
):
    """A rollback restores the token, removes the account and emits no success."""
    token, invitation = issue_invitation()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.accept_invitation(token, PASSWORD)
        assert invitation_logs.records == []
        raise RuntimeError("caller rolled back")

    assert callbacks == []
    assert invitation_logs.records == []
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()
