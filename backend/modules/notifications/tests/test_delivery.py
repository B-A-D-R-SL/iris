# AI contribution: 50% or more AI-generated
"""The real worker tracks transport attempts and exposes only safe outcomes."""

import logging
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from django.utils import translation

from adapters.mailer.base import MailerError
from adapters.mailer.fake import get_fake_mailer
from modules.notifications.models import EmailLog
from modules.notifications.tasks import DeliveryFailure, send_email

# Direct tests intentionally run without a worker-injected JobContext.
DIRECT_CONTEXT: Any = None


pytestmark = pytest.mark.django_db
DELAYS = [60, 300, 900]


@pytest.fixture
def pending_log() -> EmailLog:
    return EmailLog.objects.create(
        to_email="recipient@example.test", template_key="file_approved", language="en"
    )


@pytest.fixture
def notification_events(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
):
    logger = logging.getLogger("iris.notifications")
    monkeypatch.setattr(logger, "propagate", False)
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger=logger.name):
            yield caplog
    finally:
        logger.removeHandler(caplog.handler)


def test_delivery_uses_saved_language_and_records_acceptance_once(
    pending_log: EmailLog,
) -> None:
    with translation.override("fr"):
        send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    [message] = get_fake_mailer().sent
    assert message["to"] == ["recipient@example.test"]
    assert "approved" in message["subject"].lower()
    assert message["text"] and message["html"]
    pending_log.refresh_from_db()
    assert pending_log.status == EmailLog.Status.SENT
    assert pending_log.attempts == 1
    assert pending_log.sent_at is not None
    accepted_at = pending_log.sent_at
    send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    pending_log.refresh_from_db()
    assert len(get_fake_mailer().sent) == 1
    assert pending_log.attempts == 1
    assert pending_log.sent_at == accepted_at


def test_three_retries_end_in_failure_after_four_transport_attempts(
    pending_log: EmailLog,
) -> None:
    get_fake_mailer().error = MailerError("transport_unavailable")
    for attempt in range(1, 5):
        with pytest.raises(DeliveryFailure, match="^transport_unavailable$"):
            send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
        pending_log.refresh_from_db()
        assert pending_log.attempts == attempt
        assert pending_log.sent_at is None
        assert pending_log.status == (
            EmailLog.Status.RETRYING if attempt <= 3 else EmailLog.Status.FAILED
        )
    get_fake_mailer().error = None
    send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    assert get_fake_mailer().sent == []


def test_successful_retry_clears_previous_error(pending_log: EmailLog) -> None:
    get_fake_mailer().error = MailerError("transport_unavailable")
    with pytest.raises(DeliveryFailure):
        send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    get_fake_mailer().error = None
    send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    pending_log.refresh_from_db()
    assert pending_log.status == EmailLog.Status.SENT
    assert pending_log.attempts == 2
    assert pending_log.error == ""


def test_permanent_provider_rejection_fails_without_retry(
    pending_log: EmailLog,
) -> None:
    get_fake_mailer().error = MailerError("provider_rejected", retryable=False)
    with pytest.raises(DeliveryFailure) as caught:
        send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    assert caught.value.retryable is False
    pending_log.refresh_from_db()
    assert pending_log.status == EmailLog.Status.FAILED
    assert pending_log.attempts == 1
    assert pending_log.error == "provider_rejected"


def test_transport_refusing_the_message_is_a_retryable_failure(
    pending_log: EmailLog,
) -> None:
    get_fake_mailer().result = 0
    with pytest.raises(DeliveryFailure, match="^provider_rejected$"):
        send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    pending_log.refresh_from_db()
    assert pending_log.status == EmailLog.Status.RETRYING
    assert pending_log.attempts == 1


def test_unexpected_transport_exception_never_enters_log_records_or_metadata(
    pending_log: EmailLog,
    monkeypatch: pytest.MonkeyPatch,
    notification_events: pytest.LogCaptureFixture,
) -> None:
    secret = "recipient@example.test token=private-secret message body"

    def broken_transport(*args: Any, **kwargs: Any) -> int:
        raise ConnectionError(secret)

    monkeypatch.setattr(get_fake_mailer(), "send", broken_transport)
    with pytest.raises(DeliveryFailure) as caught:
        send_email(DIRECT_CONTEXT, str(pending_log.pk), {}, DELAYS)
    assert str(caught.value) == "transport_unavailable"
    assert caught.value.__suppress_context__ is True
    pending_log.refresh_from_db()
    assert pending_log.error == "transport_unavailable"
    assert notification_events.records
    for record in notification_events.records:
        assert record.exc_info is None
        assert record.args == ()
        assert secret not in str(vars(record))
        assert pending_log.to_email not in str(vars(record))
        assert "private-secret" not in str(vars(record))


def test_invalid_template_context_stops_before_transport(pending_log: EmailLog) -> None:
    with pytest.raises(DeliveryFailure) as caught:
        send_email(
            DIRECT_CONTEXT,
            str(pending_log.pk),
            {"reason": "private case notes"},
            DELAYS,
        )
    assert caught.value.retryable is False
    pending_log.refresh_from_db()
    assert pending_log.status == EmailLog.Status.FAILED
    assert pending_log.error == "email_configuration_invalid"
    assert pending_log.attempts == 0
    assert get_fake_mailer().sent == []


def test_missing_delivery_record_is_a_safe_noop() -> None:
    send_email(DIRECT_CONTEXT, str(uuid4()), {}, DELAYS)
    assert get_fake_mailer().sent == []


def test_final_native_job_attempt_fails_even_when_provider_attempts_are_fewer(
    pending_log: EmailLog,
) -> None:
    """Earlier worker/database failures also consume the queue's retry budget."""
    EmailLog.objects.filter(pk=pending_log.pk).update(attempts=1)
    get_fake_mailer().error = MailerError("transport_unavailable")
    job_context: Any = SimpleNamespace(job=SimpleNamespace(attempts=3))
    with pytest.raises(DeliveryFailure):
        send_email(job_context, str(pending_log.pk), {}, DELAYS)
    pending_log.refresh_from_db()
    assert pending_log.status == EmailLog.Status.FAILED
    assert pending_log.attempts == 2
