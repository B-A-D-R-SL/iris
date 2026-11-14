# AI contribution: 50% or more AI-generated
"""US-18 approval side effects: email, rollback, concurrency, states and logs."""

import json
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Barrier
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, transaction
from django.utils.translation import gettext

from adapters.mailer.fake import get_fake_mailer
from iris.observability import JsonLogFormatter
from modules.accounts import services as account_services
from modules.audit import services as audit_services
from modules.households.approval_services import approve_walk_in
from modules.households.models import Household
from modules.households.tests.approval.helpers import (
    DIRECT_CONTEXT,
    assert_unapproved,
    audit_events,
    decisions,
    invitations,
    notices,
    submit,
    submit_and_approve,
)
from modules.households.tests.factories import MemberFactory
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]


def test_email_is_sent_after_commit_and_accepts_invitation(
    household: Any,
    staff: Any,
    settings: Any,
    email_jobs: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
) -> None:
    settings.PUBLIC_APP_ORIGIN = "https://iris.example.test"
    Household.objects.filter(pk=household.pk).update(
        email="holder@example.test", preferred_language="en"
    )
    with django_capture_on_commit_callbacks(execute=True):
        submit_and_approve(household, staff)
        assert email_jobs == []
        invitation = invitations().get()
        assert invitation.role == "beneficiary"
        assert invitation.invited_by_id == staff.pk
    [job] = email_jobs
    send_email(DIRECT_CONTEXT, **job)
    [message] = get_fake_mailer().sent
    assert message["to"] == ["holder@example.test"]
    assert message["subject"] == "Set up your Iris access"
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert (log.template_key, log.status) == ("walk_in_set_password", "sent")
    token = message["text"].split("/invitation/", 1)[1].strip()
    assert token not in repr(EmailLog.objects.values().get(pk=log.pk))
    assert sha256(token.encode()).hexdigest() == invitation.token_hash
    assert token not in str(list(invitations().values()))
    user = account_services.accept_invitation(token, "Uncommon-secret-9146!")
    assert user.email == "holder@example.test"
    assert user.role == "beneficiary"


def test_an_email_with_an_account_is_approved_without_an_invitation(
    household: Any,
    staff: Any,
    email_jobs: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
) -> None:
    """The household is served at the counter; staff are told no email goes out."""
    Household.objects.filter(pk=household.pk).update(email=staff.email)
    with django_capture_on_commit_callbacks(execute=True):
        result = submit_and_approve(household, staff)
    assert result.status == "approved"
    assert result.invitation_not_sent is True
    household.refresh_from_db()
    assert household.status == "approved"
    assert not invitations().exists()
    assert email_jobs == []
    assert audit_events(household).get().metadata == {"outcome": "approved"}


def test_a_member_who_turns_18_after_submission_sends_the_file_to_review(
    household: Any, staff: Any
) -> None:
    """Notices are locked after submission, so the file cannot stay stuck."""
    submit(household)
    MemberFactory(household=household, relation="spouse_partner")
    result = approve_walk_in(household, staff)
    assert result.status == "review_required"
    assert result.status_reason == "NOTICE_MISSING"
    assert not decisions(household).exists()
    assert audit_events(household).get().metadata == {"outcome": "review_required"}


def test_audit_failure_rolls_back_all_writes(
    household: Any, staff: Any, monkeypatch: Any
) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise ValidationError("Audit unavailable")

    monkeypatch.setattr(audit_services, "record", fail)
    with pytest.raises(ValidationError, match="Audit unavailable"):
        submit_and_approve(household, staff)
    assert_unapproved(household, "submitted")
    assert not decisions(household).exists()


def test_outer_rollback_sends_no_email(
    household: Any,
    staff: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    Household.objects.filter(pk=household.pk).update(email="holder@example.test")
    submit(household)
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError, match="Cancel"),
        transaction.atomic(),
    ):
        approve_walk_in(household, staff)
        raise RuntimeError("Cancel")
    assert callbacks == []
    assert not EmailLog.objects.exists()
    assert_unapproved(household, "submitted")
    assert not decisions(household).exists()
    assert not audit_events(household).exists()


def test_repeated_stale_request_does_not_duplicate_approval(
    household: Any, staff: Any
) -> None:
    submit_and_approve(household, staff)
    with pytest.raises(ValidationError):
        submit_and_approve(household, staff)
    assert decisions(household).count() == 1
    assert audit_events(household).count() == 1


@pytest.mark.django_db(transaction=True)
def test_simultaneous_approvals_create_one_decision_and_invitation(
    household: Any,
    staff: Any,
    email_jobs: list[dict[str, Any]],
) -> None:
    Household.objects.filter(pk=household.pk).update(email="holder@example.test")
    submit(household)
    barrier = Barrier(2)

    def approve() -> str:
        close_old_connections()
        try:
            actor = get_user_model().objects.get(pk=staff.pk)
            stale = Household.objects.get(pk=household.pk)
            barrier.wait(timeout=10)
            try:
                return approve_walk_in(stale, actor).status
            except ValidationError:
                return "refused"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: approve(), range(2)))

    assert sorted(results) == ["approved", "refused"]
    assert decisions(household).count() == 1
    assert audit_events(household).count() == 1
    assert invitations().count() == 1
    assert EmailLog.objects.filter(template_key="walk_in_set_password").count() == 1
    assert len(email_jobs) == 1


# rule: BR-DUP-002
def test_a_draft_must_be_submitted_before_approval(household: Any, staff: Any) -> None:
    with pytest.raises(ValidationError) as refused:
        approve_walk_in(household, staff)
    assert refused.value.messages == [gettext("Submit the file before approving it.")]
    assert_unapproved(household, "draft")
    assert not decisions(household).exists()


# rule: BR-DUP-002
def test_a_file_in_review_cannot_be_approved_again(household: Any, staff: Any) -> None:
    """Approving again could not change the outcome; it would only repeat rows."""
    Household.objects.filter(pk=household.pk).update(
        status="review_required", status_reason="POSSIBLE_DUPLICATE"
    )
    with pytest.raises(ValidationError) as refused:
        approve_walk_in(household, staff)
    assert refused.value.messages == [
        gettext("This file is already waiting for review.")
    ]
    household.refresh_from_db()
    assert household.status_reason == "POSSIBLE_DUPLICATE"
    assert not decisions(household).exists()
    assert not audit_events(household).exists()


def test_the_decision_is_logged_after_commit(
    household: Any,
    staff: Any,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: Any,
) -> None:
    submit(household)
    with (
        caplog.at_level("INFO", logger="iris.households"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        approve_walk_in(household, staff)
    event = next(r for r in caplog.records if r.getMessage() == "walk_in_decision")
    payload = json.loads(JsonLogFormatter().format(event))
    assert payload["household_id"] == str(household.pk)
    assert payload["outcome"] == "approved"
    assert "reason_codes" not in payload


def test_a_review_decision_logs_its_reason_codes(
    household: Any,
    staff: Any,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """The production formatter keeps the outcome and codes (Massimo's review)."""
    notices(household).update(name_on_notice="Different Person", seen_in_person=False)
    submit(household)
    with (
        caplog.at_level("INFO", logger="iris.households"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        approve_walk_in(household, staff)
    event = next(r for r in caplog.records if r.getMessage() == "walk_in_decision")
    payload = json.loads(JsonLogFormatter().format(event))
    assert payload["outcome"] == "review_required"
    assert payload["reason_codes"] == "NAME_MISMATCH,NOTICE_NOT_SEEN"
