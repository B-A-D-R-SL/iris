# AI contribution: 50% or more AI-generated
"""Household emails queued after a successful commit: status changes and password setup."""

import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext, override

from adapters.mailer.base import Mailer
from adapters.mailer.smtp import SmtpMailer
from modules.notifications.tasks import send_household_status_email

logger = logging.getLogger("iris.notifications")


def _send(mailer: Mailer, email: str, subject: str, body: str) -> None:
    try:
        if mailer.send([email], subject, text=body) != 1:
            raise RuntimeError("Email was not accepted")
    except Exception:  # noqa: BLE001 - delivery cannot roll back a committed approval.
        # Provider errors may contain the recipient or the secret invitation link.
        logger.error(
            "set_password_email_failed", extra={"event": "set_password_email_failed"}
        )


def _setup_link(token: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    parsed = urlsplit(base)
    if (
        not (
            parsed.scheme == "https"
            or (
                parsed.scheme == "http"
                and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            )
        )
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValidationError(
            gettext("The invitation website URL is not configured correctly.")
        )
    return f"{base}/invitation/{token}"


def queue_set_password_email(
    *,
    email: str,
    token: str,
    language: str,
    mailer: Mailer | None = None,
) -> None:
    link = _setup_link(token)
    with override("en" if language == "en" else "fr"):
        subject = gettext("Set your Iris password")
        body = (
            gettext(
                "Your household file is approved. Use this link to set your password:"
            )
            + f"\n\n{link}"
        )
    sender = mailer if mailer is not None else _default_mailer()
    transaction.on_commit(lambda: _send(sender, email, subject, body))


def _default_mailer() -> Mailer:
    # Console and file backends would persist the secret setup link outside its tables.
    if settings.MAILERS["default"]["BACKEND"] in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
    }:
        raise ValidationError(gettext("Invitation email delivery is not configured."))
    return SmtpMailer()


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


def queue_household_status_email(
    *,
    email: str | None,
    language: str,
    status: str,
    reason: str,
) -> None:
    """Enqueue a localized notice after commit; files without email are skipped."""
    if not email:
        return
    messages = _MESSAGES["en" if language == "en" else "fr"]
    subject, body = messages[status]
    transaction.on_commit(
        lambda: send_household_status_email.defer(
            email=email, subject=subject, body=body.format(reason=reason)
        )
    )
