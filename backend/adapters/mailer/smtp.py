# AI contribution: 50% or more AI-generated
"""SMTP mail adapter: routes development messages through Mailpit."""

import logging
from collections.abc import Sequence
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from adapters.mailer.base import MailerError

logger = logging.getLogger("iris.mailer")


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
        except (SMTPException, OSError) as exc:
            logger.error(
                "email_send_failed",
                extra={
                    "event": "email_send_failed",
                    "exc_type": type(exc),
                    "reason": (
                        "smtp_error"
                        if isinstance(exc, SMTPException)
                        else "connection_error"
                    ),
                },
            )
            raise MailerError("Email delivery failed.") from exc
