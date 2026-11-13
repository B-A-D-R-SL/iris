# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Validated write operations for the stores module."""

from collections.abc import Mapping
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from modules.categories import queries as category_queries
from modules.notifications import services as notification_services
from modules.stores.models import (
    ApplicationLanguage,
    ApplicationStatus,
    PartnerApplication,
    Store,
)

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


def submit_application(
    values: Mapping[str, Any], *, language: str
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
            notification_services.send(
                email,
                "partner_application_received",
                {
                    "language": application.language,
                    "business_name": application.business_name,
                },
            )
    except IntegrityError:
        if _has_open_application(email):
            raise ApplicationAlreadyOpen(email) from None
        raise
    return application
