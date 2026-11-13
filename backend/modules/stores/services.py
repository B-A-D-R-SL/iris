# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Validated write operations for the stores module."""

import logging
from collections.abc import Mapping
from ipaddress import ip_address
from typing import Any, cast
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
    ValidationError,
)
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.categories import queries as category_queries
from modules.notifications import services as notification_services
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


class ApplicationAlreadyDecided(Exception):
    """The application is no longer awaiting a decision."""


def _require_active_admin(admin: Any) -> None:
    """Authorize before inspecting deployment configuration or taking locks."""
    if (
        not admin
        or not admin.is_authenticated
        or not admin.is_active
        or admin.role != "admin"
    ):
        raise PermissionDenied("An active admin is required.")


def can_decide_application(application: PartnerApplication, admin: Any) -> bool:
    """Decision availability for both API presentation and service enforcement."""
    try:
        _require_active_admin(admin)
    except PermissionDenied:
        return False
    return application.status == ApplicationStatus.SUBMITTED


def _loopback_host(host: str | None) -> bool:
    """Permit plaintext links only on explicit development loopback hosts."""
    if host == "localhost":
        return True
    try:
        return ip_address(host or "").is_loopback
    except ValueError:
        return False


def _frontend_origin() -> str:
    """Fail explicitly on deployment mistakes before acquiring an application lock."""
    value = settings.PUBLIC_APP_ORIGIN
    try:
        if not isinstance(value, str):
            raise ValidationError("Invalid origin")
        value = value.rstrip("/")
        URLValidator(schemes=["https", "http"])(value)
        parts = urlsplit(value)
        if (
            parts.path
            or "?" in value
            or "#" in value
            or parts.username
            or parts.password
            or (parts.scheme == "http" and not _loopback_host(parts.hostname))
        ):
            raise ValidationError("Invalid origin")
    except (ValidationError, ValueError) as exc:
        raise ImproperlyConfigured(
            "PUBLIC_APP_ORIGIN must be an HTTPS origin; HTTP is allowed only for loopback development."
        ) from exc
    return value


def _locked_application(
    application: PartnerApplication, admin: Any
) -> PartnerApplication:
    _require_active_admin(admin)
    locked = PartnerApplication.objects.select_for_update().get(pk=application.pk)
    if not can_decide_application(locked, admin):
        raise ApplicationAlreadyDecided
    return locked


def _record_decision(application: PartnerApplication, admin: Any) -> None:
    """Persist the decision and audit atomically; log success only after commit."""
    from modules.audit import services as audit_services

    application.decided_by = admin
    application.decided_at = timezone.now()
    application.save(
        update_fields=["status", "decided_by", "decided_at", "decision_reason"]
    )
    audit_services.record(
        admin,
        "decision",
        "partner_application",
        application.pk,
        {"outcome": application.status},
    )
    event = f"partner_application_{application.status}"
    transaction.on_commit(lambda: logger.info(event, extra={"event": event}))


@transaction.atomic
def approve_application(
    application: PartnerApplication, admin: Any
) -> PartnerApplication:
    """Create the store and manager invitation atomically, then queue email after commit."""
    from modules.accounts import services as account_services

    _require_active_admin(admin)
    base_url = _frontend_origin()
    application = _locked_application(application, admin)
    store = Store(
        name=application.business_name,
        street_number=application.street_number,
        street_name=application.street_name,
        unit=application.unit,
        city=application.city,
        postal_code=application.postal_code,
        phone=application.contact_phone,
        email=application.contact_email,
        opening_hours={"notes": application.opening_hours},
        application=application,
    )
    store.full_clean()
    store.save()
    token = account_services.create_invitation(
        email=application.contact_email,
        first_name=application.contact_first_name,
        last_name=application.contact_last_name,
        role="store_manager",
        store=store,
        invited_by=admin,
    )
    application.status = ApplicationStatus.APPROVED
    application.decision_reason = None
    _record_decision(application, admin)
    notification_services.send(
        application.contact_email,
        "partner_application_approved",
        {
            "language": application.language,
            "invitation_url": f"{base_url}/invitation/{token}",
        },
    )
    return application


@transaction.atomic
def resend_approval_invitation(application: PartnerApplication, admin: Any) -> None:
    """Reissue an approved application's invitation; send only after commit."""
    from modules.accounts import services as account_services

    _require_active_admin(admin)
    base_url = _frontend_origin()
    application = PartnerApplication.objects.select_for_update().get(pk=application.pk)
    if application.status != ApplicationStatus.APPROVED:
        raise ValidationError(
            "Only approved applications can have invitations reissued."
        )
    store = Store.objects.get(application=application)
    token = account_services.reissue_store_manager_invitation(
        email=application.contact_email,
        first_name=application.contact_first_name,
        last_name=application.contact_last_name,
        store=store,
        invited_by=admin,
    )
    notification_services.send(
        application.contact_email,
        "partner_application_approved",
        {
            "language": application.language,
            "invitation_url": f"{base_url}/invitation/{token}",
        },
    )


@transaction.atomic
def reject_application(
    application: PartnerApplication,
    admin: Any,
    reason: str,
) -> PartnerApplication:
    """Record a rejection and notify the applicant after the transaction commits."""
    application = _locked_application(application, admin)
    # BR-PARTNER-04: derive the fixed API/storage bound from its model field.
    reason_limit = cast(
        int, PartnerApplication._meta.get_field("decision_reason").max_length
    )
    if (
        not isinstance(reason, str)
        or not reason.strip()
        or len(reason.strip()) > reason_limit
    ):
        raise ValidationError(
            {"reason": _("Enter a reason of at most 500 characters.")}
        )
    reason = reason.strip()
    application.status = ApplicationStatus.REJECTED
    application.decision_reason = reason
    _record_decision(application, admin)
    notification_services.send(
        application.contact_email,
        "partner_application_rejected",
        {"language": application.language, "reason": reason},
    )
    return application
