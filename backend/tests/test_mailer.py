# AI contribution: 50% or more AI-generated
"""SMTP delivery failures have a typed boundary and privacy-safe diagnostics."""

import json
import logging
from io import StringIO
from smtplib import (  # noqa: TID251 - exception fixtures only; no SMTP connection.
    SMTPAuthenticationError,
    SMTPDataError,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
)
from socket import gaierror
from ssl import SSLError
from unittest.mock import Mock

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.test import override_settings

from adapters.mailer.base import MailerError
from adapters.mailer.smtp import SmtpMailer
from iris.observability import JsonLogFormatter

PRIVATE = "private@example.test secret-subject secret-body"


@pytest.fixture
def mail_logs():
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("iris.mailer")
    logger.addHandler(handler)
    try:
        yield output
    finally:
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.parametrize(
    ("error", "reason", "code", "retryable", "smtp_code"),
    [
        (
            SMTPAuthenticationError(535, PRIVATE.encode()),
            "smtp_error",
            "provider_rejected",
            False,
            535,
        ),
        (
            SMTPRecipientsRefused({PRIVATE: (550, PRIVATE.encode())}),
            "smtp_error",
            "provider_rejected",
            False,
            None,
        ),
        (
            SMTPRecipientsRefused({PRIVATE: (450, PRIVATE.encode())}),
            "smtp_error",
            "provider_rejected",
            True,
            None,
        ),
        (
            SMTPDataError(451, PRIVATE.encode()),
            "smtp_error",
            "provider_rejected",
            True,
            451,
        ),
        (
            SMTPDataError(554, PRIVATE.encode()),
            "smtp_error",
            "provider_rejected",
            False,
            554,
        ),
        (
            SMTPServerDisconnected(PRIVATE),
            "smtp_error",
            "transport_unavailable",
            True,
            None,
        ),
        (
            ConnectionRefusedError(PRIVATE),
            "connection_error",
            "transport_unavailable",
            True,
            None,
        ),
        (
            TimeoutError(PRIVATE),
            "connection_error",
            "transport_unavailable",
            True,
            None,
        ),
        (gaierror(PRIVATE), "connection_error", "transport_unavailable", True, None),
        (SSLError(PRIVATE), "connection_error", "transport_unavailable", True, None),
    ],
)
def test_transport_failure_is_logged_and_raised_as_mailer_error(
    monkeypatch, mail_logs, error, reason, code, retryable, smtp_code
):
    send = Mock(side_effect=error)
    monkeypatch.setattr(EmailMultiAlternatives, "send", send)
    with pytest.raises(MailerError, match=f"^{code}$") as raised:
        SmtpMailer().send(
            ["private@example.test"], "secret-subject", text="secret-body"
        )
    assert raised.value.code == code
    assert raised.value.retryable is retryable
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    send.assert_called_once_with(fail_silently=False)
    [event] = [json.loads(line) for line in mail_logs.getvalue().splitlines()]
    expected = {
        "timestamp": event["timestamp"],
        "level": "ERROR",
        "logger": "iris.mailer",
        "event": "email_send_failed",
        "exc_type": type(error).__name__,
        "reason": reason,
    }
    if smtp_code is not None:
        expected["smtp_code"] = smtp_code
    assert event == expected


@pytest.mark.parametrize(
    ("recipients", "text"), [([], "body"), (["private@example.test"], None)]
)
def test_invalid_message_stays_a_validation_error(
    monkeypatch, mail_logs, recipients, text
):
    send = Mock()
    monkeypatch.setattr(EmailMultiAlternatives, "send", send)
    with pytest.raises(ValueError):
        SmtpMailer().send(recipients, "subject", text=text)
    send.assert_not_called()
    assert mail_logs.getvalue() == ""


def test_unexpected_provider_errors_are_sanitized_and_logged(monkeypatch, mail_logs):
    monkeypatch.setattr(
        EmailMultiAlternatives, "send", Mock(side_effect=TypeError(PRIVATE))
    )
    with pytest.raises(MailerError, match="^transport_unavailable$") as raised:
        SmtpMailer().send(["private@example.test"], "subject", text="body")
    assert raised.value.retryable is True
    assert raised.value.__suppress_context__ is True
    [event] = [json.loads(line) for line in mail_logs.getvalue().splitlines()]
    assert event["exc_type"] == "TypeError"
    assert event["reason"] == "transport_error"
    assert PRIVATE not in mail_logs.getvalue()


@override_settings(
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
    DEFAULT_FROM_EMAIL="noreply@iris.local",
)
@pytest.mark.parametrize("text", [None, "plain body"])
def test_html_delivery_still_succeeds_without_a_failure_event(mail_logs, text):
    assert (
        SmtpMailer().send(
            ["recipient@example.test"], "subject", html="<p>body</p>", text=text
        )
        == 1
    )
    [message] = mail.outbox
    assert message.to == ["recipient@example.test"]
    assert message.body == (text or "")
    assert message.alternatives == [("<p>body</p>", "text/html")]
    assert mail_logs.getvalue() == ""
