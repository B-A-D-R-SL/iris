# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Validated write operations for the stores module."""

import logging
from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import translation
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from adapters.mailer.base import Mailer
from adapters.mailer.smtp import SmtpMailer
from modules.categories import queries as category_queries
from modules.stores.models import (
    ApplicationLanguage,
    ApplicationStatus,
    PartnerApplication,
    Store,
)

logger = logging.getLogger("iris.stores")

UNKNOWN_CATEGORY_MESSAGE = _("Choose types of goods from the list.")

BADR_STORE_DEFAULTS = {
    "name": "B.A.D.R.",
    "street_number": "0000",
    "street_name": "rue Exemple",
    "city": "Montreal",
    "postal_code": "H0H 0H0",
    "phone": "+15145550100",
    "email": "badr-store@example.test",
    "opening_hours": {},
    "is_active": True,
}


@transaction.atomic
def save_store(store: Store) -> Store:
    """Validate and persist a Store submitted through Django admin."""
    store.full_clean()
    store.save()
    return store


@transaction.atomic
def ensure_badr_store() -> tuple[Store, bool]:
    """Create the placeholder B.A.D.R. store once without changing later edits."""
    return Store.objects.get_or_create(is_badr=True, defaults=BADR_STORE_DEFAULTS)


class ApplicationAlreadyOpen(Exception):
    """A submitted application with the same contact email awaits a decision."""

    def __init__(self, email: str) -> None:
        super().__init__(email)
        self.email = email


def _has_open_application(email: str) -> bool:
    return PartnerApplication.objects.filter(
        contact_email=email, status=ApplicationStatus.SUBMITTED
    ).exists()


def _check_categories(codes: list[str]) -> None:
    active = set(
        category_queries.list_active_categories().values_list("code", flat=True)
    )
    if not codes or not set(codes) <= active:
        raise ValidationError({"goods_categories": [UNKNOWN_CATEGORY_MESSAGE]})


def _confirmation_email(application: PartnerApplication) -> tuple[str, str]:
    """Render the partner_application_received email in the contact's language."""
    with translation.override(application.language):
        subject = gettext("We received your partner application")
        lines = [
            gettext("Hello,"),
            gettext(
                "Thank you for applying to become a B.A.D.R. partner store with "
                "Iris. We received the application for %(business)s."
            )
            % {"business": application.business_name},
            gettext(
                "B.A.D.R. will review it and write to you at this address. "
                "You have nothing else to do for now."
            ),
            gettext("The Iris team"),
        ]
    return subject, "\n\n".join(lines)


def _send_confirmation(mailer: Mailer, to: str, subject: str, body: str) -> None:
    try:
        mailer.send([to], subject, text=body)
    except Exception:  # noqa: BLE001 - the saved application must not be lost.
        # No address, names or provider error text: logs never hold personal data.
        logger.error("partner_application_email_failed")


def submit_application(
    values: Mapping[str, Any], *, language: str, mailer: Mailer | None = None
) -> PartnerApplication:
    """Save a submitted application, then email the contact after the commit.

    Values arrive validated and normalized by the API serializer. No account is
    created; an admin decides the application later (US-13).
    """
    email = values["contact_email"]
    if _has_open_application(email):
        raise ApplicationAlreadyOpen(email)
    _check_categories(list(values["goods_categories"]))

    application = PartnerApplication(
        **values,
        language=language
        if language in ApplicationLanguage.values
        else ApplicationLanguage.FRENCH,
        status=ApplicationStatus.SUBMITTED,
    )
    # The partial unique index decides races between simultaneous submissions.
    application.full_clean(validate_constraints=False)
    try:
        with transaction.atomic():
            application.save()
            subject, body = _confirmation_email(application)
            sender = mailer if mailer is not None else SmtpMailer()
            transaction.on_commit(
                lambda: _send_confirmation(sender, email, subject, body)
            )
    except IntegrityError:
        if _has_open_application(email):
            raise ApplicationAlreadyOpen(email) from None
        raise
    return application
