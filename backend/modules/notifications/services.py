# AI contribution: 50% or more AI-generated
"""Household status email delivery after a successful commit."""

import logging

from django.db import transaction

from adapters.mailer.base import Mailer
from adapters.mailer.smtp import SmtpMailer

logger = logging.getLogger("iris.notifications")

_MESSAGES = {
    "en": {
        "suspended": (
            "Your Iris household file was suspended",
            "Your household file was suspended. Reason: {reason}",
        ),
        "approved": (
            "Your Iris household file was reactivated",
            "Your household file was reactivated. Reason: {reason}",
        ),
    },
    "fr": {
        "suspended": (
            "Votre dossier de foyer Iris a été suspendu",
            "Votre dossier de foyer a été suspendu. Motif : {reason}",
        ),
        "approved": (
            "Votre dossier de foyer Iris a été réactivé",
            "Votre dossier de foyer a été réactivé. Motif : {reason}",
        ),
    },
}


def _send(mailer: Mailer, email: str, subject: str, body: str) -> None:
    try:
        if mailer.send([email], subject, text=body) != 1:
            raise RuntimeError("Email was not accepted")
    except Exception:  # noqa: BLE001 - delivery cannot undo a committed change.
        logger.error(
            "household_status_email_failed",
            extra={"event": "household_status_email_failed"},
        )


def queue_household_status_email(
    *,
    email: str | None,
    language: str,
    status: str,
    reason: str,
    mailer: Mailer | None = None,
) -> None:
    """Send a localized notice after commit; counter-only files have no email."""
    if not email:
        return
    messages = _MESSAGES["en" if language == "en" else "fr"]
    subject, body = messages[status]
    sender = mailer if mailer is not None else SmtpMailer()
    transaction.on_commit(
        lambda: _send(sender, email, subject, body.format(reason=reason))
    )
