# AI contribution: 50% or more AI-generated
"""SMTP delivery with safe diagnostics and the shared retryable error contract."""

import logging
from collections.abc import Sequence
from smtplib import SMTPException, SMTPRecipientsRefused, SMTPResponseException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from adapters.mailer.base import MailerError

logger = logging.getLogger("iris.mailer")


def _log_delivery_failure(exc: Exception) -> None:
    """Record types and numeric response codes, never provider text or recipients."""
    reason = (
        "smtp_error"
        if isinstance(exc, SMTPException)
        else "connection_error"
        if isinstance(exc, OSError)
        else "transport_error"
    )
    fields: dict[str, object] = {
        "event": "email_send_failed",
        "exc_type": type(exc),
        "reason": reason,
    }
    if isinstance(exc, SMTPResponseException):
        code = exc.smtp_code
        if type(code) is int and 400 <= code <= 599:
            fields["smtp_code"] = code
    logger.error("email_send_failed", extra=fields)


def _delivery_error(exc: Exception) -> MailerError:
    """Keep the notification worker's retry classification and bounded codes."""
    if isinstance(exc, SMTPRecipientsRefused):
        return MailerError(
            "provider_rejected",
            retryable=any(400 <= code < 500 for code, _ in exc.recipients.values()),
        )
    if isinstance(exc, SMTPResponseException):
        return MailerError("provider_rejected", retryable=400 <= exc.smtp_code < 500)
    return MailerError("transport_unavailable")


class SmtpMailer:
    def send(
        self,
        to: Sequence[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
    ) -> int:
        if not to:
            raise ValueError("At least one recipient is required")
        if html is None and text is None:
            raise ValueError("At least one email body (text or html) is required")

        message = EmailMultiAlternatives(
            subject=subject,
            body=text or "",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=list(to),
        )
        if html is not None:
            message.attach_alternative(html, "text/html")
        try:
            return message.send(fail_silently=False)
        except Exception as exc:  # noqa: BLE001 - provider text must not reach queued jobs.
            _log_delivery_failure(exc)
            raise _delivery_error(exc) from None
