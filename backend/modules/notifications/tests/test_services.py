# AI contribution: 50% or more AI-generated
"""Delivery metadata and queueing follow the originating transaction."""

import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from procrastinate.contrib.django import app

from adapters.mailer.fake import get_fake_mailer
from modules.accounts.tests.factories import UserFactory
from modules.notifications import services
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace queue transport, preserving the production service and database."""
    jobs: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: jobs.append(kwargs))
    return jobs


@pytest.fixture
def notification_events(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> Iterator[pytest.LogCaptureFixture]:
    logger = logging.getLogger("iris.notifications")
    monkeypatch.setattr(logger, "propagate", False)
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger=logger.name):
            yield caplog
    finally:
        logger.removeHandler(caplog.handler)


# rule: BR-NOTIF-001
# rule: BR-NOTIF-002
# rule: BR-NOTIF-003
def test_log_and_job_capture_recipient_and_context_before_the_outer_commit(
    queued: list[dict[str, Any]], django_capture_on_commit_callbacks: Any
) -> None:
    user: Any = UserFactory(preferred_language="en")
    original_email = user.email
    context = {"business_name": "Generated bakery"}
    with django_capture_on_commit_callbacks(execute=True):
        with transaction.atomic():
            log = services.send(user, "partner_application_received", context)
            assert log.status == EmailLog.Status.PENDING
            assert log.user_id == user.pk
            assert log.language == "en"
            assert log.to_email == original_email
            assert queued == []
        context["business_name"] = "Changed after scheduling"
        user.preferred_language = "fr"
        user.email = "changed@example.test"
        user.save(update_fields=["email", "preferred_language"])
        assert queued == []
    [job] = queued
    assert job["email_log_id"] == str(log.pk)
    assert job["context"] == {"business_name": "Generated bakery"}
    assert job["retry_delays"] == [60, 300, 900]
    log.refresh_from_db()
    assert log.language == "en"
    assert log.to_email == original_email
    assert get_fake_mailer().sent == []


# rule: BR-NOTIF-002
def test_rollback_removes_metadata_and_discards_delivery_callback(
    queued: list[dict[str, Any]], django_capture_on_commit_callbacks: Any
) -> None:
    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(RuntimeError, match="business rollback"),
        transaction.atomic(),
    ):
        services.send("recipient@example.test", "file_approved", {"language": "en"})
        raise RuntimeError("business rollback")
    assert not EmailLog.objects.exists()
    assert queued == []
    assert get_fake_mailer().sent == []


# rule: BR-NOTIF-003
@pytest.mark.parametrize("language", ["fr", "en"])
def test_email_only_recipients_need_no_account_and_capture_explicit_locale(
    language: str, queued: list[dict[str, Any]], django_capture_on_commit_callbacks: Any
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        log = services.send(
            "visitor@example.test", "file_in_review", {"language": language}
        )
    assert log.user_id is None
    assert log.language == language
    assert queued[0]["context"] == {}


# rule: BR-NOTIF-002
def test_missing_rules_records_failure_without_losing_the_business_transaction(
    monkeypatch: pytest.MonkeyPatch,
    queued: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
) -> None:
    def unavailable() -> None:
        raise ValidationError("private configuration details")

    monkeypatch.setattr(services.rule_queries, "notification_policy", unavailable)
    with django_capture_on_commit_callbacks(execute=True):
        log = services.send("recipient@example.test", "file_approved", {})
    log.refresh_from_db()
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "notification_rules_unavailable"
    assert log.attempts == 0
    assert queued == []


# rule: BR-NOTIF-002
def test_queue_failure_is_contained_after_commit_and_persists_a_safe_error(
    monkeypatch: pytest.MonkeyPatch, django_capture_on_commit_callbacks: Any
) -> None:
    def unavailable(**kwargs: Any) -> None:
        raise ConnectionError("recipient@example.test body credentials")

    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", unavailable)
    with django_capture_on_commit_callbacks(execute=True):
        log = services.send("recipient@example.test", "file_rejected", {})
    log.refresh_from_db()
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "queue_unavailable"
    assert log.attempts == 0


# rule: BR-NOTIF-002
def test_unknown_template_is_a_programmer_error_without_delivery_metadata(
    queued: list[dict[str, Any]],
) -> None:
    with pytest.raises(ValueError, match="^Unknown email template$"):
        services.send("recipient@example.test", "unknown", {})
    assert not EmailLog.objects.exists()
    assert queued == []


# rule: BR-NOTIF-002
# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    ("recipient", "snapshot"),
    [
        ("legacy-invalid-address", "legacy-invalid-address"),
        ("", ""),
        (None, ""),
        ("a" * 64 + "@" + "b" * 63 + "." + "c" * 63 + "." + "d" * 61 + ".test", ""),
        ("unsafe\x00@example.test", ""),
        ("unsafe\ud800@example.test", ""),
    ],
)
def test_invalid_recipient_records_failure_without_queueing_or_private_logs(
    recipient: Any,
    snapshot: str,
    queued: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
    notification_events: pytest.LogCaptureFixture,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        log = services.send(recipient, "file_approved", {})
    log.refresh_from_db()
    assert log.to_email == snapshot
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_recipient_invalid"
    assert log.attempts == 0 and log.sent_at is None
    assert queued == [] and get_fake_mailer().sent == []
    [record] = notification_events.records
    assert record.getMessage() == "email_configuration_failed"
    assert record.args == () and record.exc_info is None
    if isinstance(recipient, str) and recipient:
        assert recipient not in str(vars(record))


# rule: BR-NOTIF-002
# rule: BR-NOTIF-003
@pytest.mark.parametrize("context", [{"reason": "private-notes-sentinel"}, {}, None])
@pytest.mark.django_db(transaction=True)
def test_email_context_failure_does_not_undo_an_actual_business_commit(
    context: Any,
    queued: list[dict[str, Any]],
    notification_events: pytest.LogCaptureFixture,
) -> None:
    """Email validation cannot roll back an otherwise valid persisted update."""
    user: Any = UserFactory(preferred_language="fr")
    with transaction.atomic():
        user.preferred_language = "en"
        user.save(update_fields=["preferred_language"])
        log = services.send(user, "password_reset", context)
        assert log.status == EmailLog.Status.FAILED
        assert notification_events.records == []
    user.refresh_from_db()
    log.refresh_from_db()
    assert user.preferred_language == "en"
    assert log.language == "en" and log.user_id == user.pk
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_configuration_invalid" and log.attempts == 0
    assert queued == [] and get_fake_mailer().sent == []
    [record] = notification_events.records
    assert record.getMessage() == "email_configuration_failed"
    assert record.args == () and record.exc_info is None
    assert "private-notes-sentinel" not in str(vars(record))
    assert user.email not in str(vars(record))


# rule: BR-NOTIF-002
@pytest.mark.django_db(transaction=True)
def test_runtime_origin_failure_does_not_undo_an_actual_business_commit(
    settings: Any,
    queued: list[dict[str, Any]],
    notification_events: pytest.LogCaptureFixture,
) -> None:
    user: Any = UserFactory(preferred_language="fr")
    settings.PUBLIC_APP_ORIGIN = "https://invalid-origin.example/path"
    with transaction.atomic():
        user.preferred_language = "en"
        user.save(update_fields=["preferred_language"])
        log = services.send(user, "file_approved", {})
    user.refresh_from_db()
    assert user.preferred_language == "en"
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_configuration_invalid" and log.attempts == 0
    assert queued == []
    assert len(notification_events.records) == 1


# rule: BR-NOTIF-002
def test_outer_rollback_discards_failed_email_metadata_and_failure_event(
    queued: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
    notification_events: pytest.LogCaptureFixture,
) -> None:
    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(RuntimeError, match="business rollback"),
        transaction.atomic(),
    ):
        services.send("legacy-invalid-address", "file_approved", {})
        raise RuntimeError("business rollback")
    assert not EmailLog.objects.exists()
    assert notification_events.records == []
    assert queued == []


# rule: BR-NOTIF-002
# rule: BR-NOTIF-003
def test_queue_and_metadata_write_failure_are_both_observable_without_raw_errors(
    monkeypatch: pytest.MonkeyPatch,
    notification_events: pytest.LogCaptureFixture,
) -> None:
    def unavailable(**kwargs: Any) -> None:
        raise ConnectionError("private-queue-error-sentinel")

    class UnavailableUpdate:
        def update(self, **kwargs: Any) -> None:
            raise DatabaseError("private-database-error-sentinel")

    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", unavailable)
    monkeypatch.setattr(
        EmailLog.objects, "filter", lambda **kwargs: UnavailableUpdate()
    )
    services._enqueue("00000000-0000-0000-0000-000000000001", {}, [60, 300, 900])
    assert [record.getMessage() for record in notification_events.records] == [
        "email_outcome_unavailable",
        "email_queue_failed",
    ]
    for record in notification_events.records:
        assert record.args == () and record.exc_info is None
        assert "private-queue-error-sentinel" not in str(vars(record))
        assert "private-database-error-sentinel" not in str(vars(record))


def test_counter_only_files_skip_mail_without_creating_a_log(
    queued: list[dict[str, Any]],
) -> None:
    services.queue_household_status_email(
        email=None, language="fr", status="suspended", reason="Staff case notes"
    )
    assert not EmailLog.objects.exists()
    assert queued == []


# rule: BR-NOTIF-002
# rule: BR-NOTIF-003
@pytest.mark.django_db(transaction=True)
def test_real_database_commit_creates_one_locked_job_with_metadata_only_log() -> None:
    """Use the installed queue connector, including its persistent JSON payload."""
    with transaction.atomic():
        log = services.send(
            "recipient@example.test", "file_approved", {"language": "en"}
        )
        assert app.job_manager.list_jobs(lock=f"email:{log.pk}") == []
    [job] = app.job_manager.list_jobs(lock=f"email:{log.pk}")
    assert job.lock == f"email:{log.pk}"
    # Django's raw cursor keeps JSONB as text; worker connectors decode it.
    payload = (
        json.loads(job.task_kwargs)
        if isinstance(job.task_kwargs, str)
        else job.task_kwargs
    )
    assert payload == {
        "email_log_id": str(log.pk),
        "context": {},
        "retry_delays": [60, 300, 900],
    }
    assert not {"body", "text", "html", "context", "subject"} & {
        field.name for field in EmailLog._meta.fields
    }
    assert get_fake_mailer().sent == []
