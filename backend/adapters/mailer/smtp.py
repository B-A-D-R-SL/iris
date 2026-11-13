# AI contribution: 50% or more AI-generated
"""SMTP mail adapter: routes development messages through Mailpit."""

from collections.abc import Sequence
from smtplib import SMTPRecipientsRefused, SMTPResponseException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from adapters.mailer.base import MailerError


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
        except SMTPRecipientsRefused as exc:
            raise MailerError(
                "provider_rejected",
                retryable=any(400 <= code < 500 for code, _ in exc.recipients.values()),
            ) from None
        except SMTPResponseException as exc:
            raise MailerError(
                "provider_rejected", retryable=400 <= exc.smtp_code < 500
            ) from None
        except Exception:  # noqa: BLE001 - provider details must not reach the queue.
            raise MailerError("transport_unavailable") from None
