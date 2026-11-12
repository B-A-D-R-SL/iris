# AI contribution: 50% or more AI-generated
"""SMTP delivery failures have a typed boundary and privacy-safe diagnostics."""

import json
import logging
from io import StringIO
from smtplib import (  # noqa: TID251 - exception fixtures only; no SMTP connection.
    SMTPAuthenticationError,
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
    ("error", "reason"),
    [
        (SMTPAuthenticationError(535, PRIVATE.encode()), "smtp_error"),
        (SMTPRecipientsRefused({PRIVATE: (550, PRIVATE.encode())}), "smtp_error"),
        (SMTPServerDisconnected(PRIVATE), "smtp_error"),
        (ConnectionRefusedError(PRIVATE), "connection_error"),
        (TimeoutError(PRIVATE), "connection_error"),
        (gaierror(PRIVATE), "connection_error"),
        (SSLError(PRIVATE), "connection_error"),
    ],
)
def test_transport_failure_is_logged_and_raised_as_mailer_error(
    monkeypatch, mail_logs, error, reason
):
    send = Mock(side_effect=error)
    monkeypatch.setattr(EmailMultiAlternatives, "send", send)
    with pytest.raises(MailerError, match="^Email delivery failed\\.$") as raised:
        SmtpMailer().send(
            ["private@example.test"], "secret-subject", text="secret-body"
        )
    assert raised.value.__cause__ is error
    send.assert_called_once_with(fail_silently=False)
    [event] = [json.loads(line) for line in mail_logs.getvalue().splitlines()]
    assert event == {
        "timestamp": event["timestamp"],
        "level": "ERROR",
        "logger": "iris.mailer",
        "event": "email_send_failed",
        "exc_type": type(error).__name__,
        "reason": reason,
    }


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


def test_programming_errors_are_not_misclassified_as_transport_failures(
    monkeypatch, mail_logs
):
    monkeypatch.setattr(
        EmailMultiAlternatives, "send", Mock(side_effect=TypeError(PRIVATE))
    )
    with pytest.raises(TypeError):
        SmtpMailer().send(["private@example.test"], "subject", text="body")
    assert mail_logs.getvalue() == ""


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
