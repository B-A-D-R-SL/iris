# AI contribution: 50% or more AI-generated
"""Delivery metadata and queueing follow the originating transaction."""

import json
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
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


@pytest.mark.parametrize(
    ("recipient", "key", "context"),
    [
        ("invalid-address", "file_approved", {}),
        ("recipient@example.test", "unknown", {}),
        ("recipient@example.test", "file_approved", {"reason": "private notes"}),
    ],
)
def test_invalid_requests_never_create_delivery_metadata(
    recipient: str, key: str, context: dict[str, str], queued: list[dict[str, Any]]
) -> None:
    with pytest.raises((ValidationError, ValueError)):
        services.send(recipient, key, context)
    assert not EmailLog.objects.exists()
    assert queued == []


def test_counter_only_files_skip_mail_without_creating_a_log(
    queued: list[dict[str, Any]],
) -> None:
    services.queue_household_status_email(
        email=None, language="fr", status="suspended", reason="Staff case notes"
    )
    assert not EmailLog.objects.exists()
    assert queued == []


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
