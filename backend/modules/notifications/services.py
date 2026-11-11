# AI contribution: 50% or more AI-generated
"""Household status email queueing after a successful commit."""

from django.db import transaction

from modules.notifications.tasks import send_household_status_email

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
