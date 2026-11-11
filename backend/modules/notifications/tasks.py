# AI contribution: 50% or more AI-generated
"""Background delivery jobs for household notifications."""

import logging

from procrastinate.contrib.django import app

from adapters.mailer.base import Mailer
from adapters.mailer.smtp import SmtpMailer

logger = logging.getLogger("iris.notifications")


def deliver_household_status_email(
    mailer: Mailer, email: str, subject: str, body: str
) -> None:
    """Deliver one queued notice without exposing recipient data in logs."""
    try:
        if mailer.send([email], subject, text=body) != 1:
            raise RuntimeError("Email was not accepted")
    except Exception:  # noqa: BLE001 - a queued delivery failure is logged and contained.
        logger.error(
            "household_status_email_failed",
            extra={"event": "household_status_email_failed"},
        )


@app.task(name="notifications.send_household_status_email")
def send_household_status_email(email: str, subject: str, body: str) -> None:
    """Run SMTP delivery outside the request that changed household status."""
    deliver_household_status_email(SmtpMailer(), email, subject, body)
