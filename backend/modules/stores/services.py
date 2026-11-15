# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Validated write operations for the stores module."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.categories import queries as category_queries
from modules.notifications import services as notification_services
from modules.stores.domain import store_rules
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


def _invitation_url(token: str) -> str | None:
    """Let notification validation record email configuration failures separately."""
    origin = getattr(settings, "PUBLIC_APP_ORIGIN", None)
    return (
        f"{origin.rstrip('/')}/invitation/{token}" if isinstance(origin, str) else None
    )


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
            "invitation_url": _invitation_url(token),
        },
    )
    return application


@transaction.atomic
def resend_approval_invitation(application: PartnerApplication, admin: Any) -> None:
    """Reissue an approved application's invitation; send only after commit."""
    from modules.accounts import services as account_services

    _require_active_admin(admin)
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
            "invitation_url": _invitation_url(token),
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


# --- Store administration (US-14) -------------------------------------------

# Every field an admin may change; is_badr, application, is_active, the id and
# the timestamps are never edited here (is_active only through (de)activation).
EDITABLE_STORE_FIELDS = frozenset(
    {
        "name",
        "street_number",
        "street_name",
        "unit",
        "city",
        "postal_code",
        "phone",
        "email",
        "opening_hours",
        "pickup_instructions",
    }
)
_OPTIONAL_TEXT_FIELDS = frozenset({"unit", "pickup_instructions"})

HOURS_MESSAGES = {
    store_rules.HOURS_NOT_A_WEEK: _("Enter the opening hours for every day."),
    store_rules.HOURS_INVALID_TIME: _("Enter times as HH:MM."),
    store_rules.HOURS_CLOSE_BEFORE_OPEN: _(
        "The closing time must be after the opening time."
    ),
    store_rules.HOURS_NO_OPEN_DAY: _("The store must be open at least one day."),
}
REASON_MESSAGES = {
    store_rules.REASON_REQUIRED: _("Enter a reason."),
    store_rules.REASON_TOO_LONG: _("Enter a reason of at most 500 characters."),
}
SENSITIVE_REASON_MESSAGE = _(
    "Remove personal details such as names, emails, phone numbers or ID numbers."
)


class StoreIsBadr(Exception):
    """The B.A.D.R. store is never deactivated."""


class StoreStatusUnchanged(Exception):
    """The store is already active, or already deactivated."""

    def __init__(self, *, is_active: bool) -> None:
        super().__init__("already active" if is_active else "already inactive")
        self.is_active = is_active


@dataclass(frozen=True)
class DeactivationResult:
    store: Store
    listings_cancelled: int
    reservations_cancelled: int


def _locked_store(store_id: UUID) -> Store:
    """The store row, locked for the rest of the transaction (404 when missing)."""
    return Store.objects.select_for_update().get(pk=store_id)


def _hours_errors(value: object) -> dict[str, list[str]]:
    codes = store_rules.weekly_hours_errors(value)
    if not codes:
        return {}
    return {"opening_hours": [str(HOURS_MESSAGES[code]) for code in codes.values()]}


def _apply_changes(store: Store, changes: Mapping[str, Any]) -> None:
    unknown = sorted(set(changes) - EDITABLE_STORE_FIELDS)
    if unknown:
        raise ValidationError(
            {field: _("This field cannot be changed.") for field in unknown}
        )
    for field, value in changes.items():
        if field == "opening_hours":
            if errors := _hours_errors(value):
                raise ValidationError(errors)
            value = store_rules.schedule_with_notes(value, store.opening_hours)
        elif isinstance(value, str):
            value = value.strip()
            if field in _OPTIONAL_TEXT_FIELDS and not value:
                value = None
        setattr(store, field, value)


@transaction.atomic
def update_store(store_id: UUID, changes: Mapping[str, Any], admin: Any) -> Store:
    """Change store fields; audit the changed field names, never their values.

    rule: BR-STORE-001 admin only, editable fields only, nothing recorded when
    nothing changes. Address edits show on every listing of the store.
    """
    from modules.audit import services as audit_services

    _require_active_admin(admin)
    store = _locked_store(store_id)
    before = {field: getattr(store, field) for field in changes}
    _apply_changes(store, changes)
    # Check only the submitted fields: older stores (B.A.D.R., approvals) may
    # still hold empty hours. Store.clean also normalises the postal code.
    store.full_clean(
        exclude=[f.name for f in Store._meta.fields if f.name not in changes]
    )
    changed = store_rules.changed_fields(
        before, {field: getattr(store, field) for field in changes}
    )
    if not changed:
        return Store.objects.get(pk=store.pk)
    store.save(update_fields=[*changed, "updated_at"])
    audit_services.record(
        admin, "update", "store", store.pk, {"fields": ",".join(changed)}
    )
    return store


def _status_reason(reason: object) -> str:
    """BR-STORE-005: required, at most 500 characters, no personal details."""
    from modules.privacy import services as privacy_services

    cleaned, error = store_rules.clean_reason(reason)
    if error:
        raise ValidationError({"reason": REASON_MESSAGES[error]})
    if privacy_services.household_reason_contains_sensitive_data(cleaned):
        raise ValidationError({"reason": SENSITIVE_REASON_MESSAGE})
    return cleaned


def can_change_status(store: Store) -> bool:
    """BR-STORE-004: every store but B.A.D.R. can be deactivated and reactivated.

    The admin screen shows the status switch from this, so the rule lives here only.
    """
    return not store.is_badr


def _locked_for_status_change(store_id: UUID, admin: Any, *, activate: bool) -> Store:
    _require_active_admin(admin)
    store = _locked_store(store_id)
    if not can_change_status(store):
        raise StoreIsBadr
    if store.is_active == activate:
        raise StoreStatusUnchanged(is_active=store.is_active)
    return store


@transaction.atomic
def deactivate_store(store_id: UUID, admin: Any, reason: str) -> DeactivationResult:
    """Stop a store posting and cancel what households can no longer pick up.

    rule: BR-STORE-004 never the B.A.D.R. store. One transaction: the store,
    its listings whose pickup has not ended (BR-STORE-002), their reserved
    claims and emails (BR-STORE-003) and the audit event all commit together.
    """
    from modules.audit import services as audit_services
    from modules.listings import services as listing_services
    from modules.reservations import services as reservation_services

    store = _locked_for_status_change(store_id, admin, activate=False)
    reason = _status_reason(reason)
    now = timezone.now()  # read after the lock, like the reservation clock
    store.is_active = False
    store.save(update_fields=["is_active", "updated_at"])
    listing_ids = listing_services.cancel_all_for_store(store.pk, now=now)
    reservations = reservation_services.cancel_for_cancelled_listings(
        listing_ids, store_name=store.name
    )
    audit_services.record(
        admin,
        "deactivate",
        "store",
        store.pk,
        {
            "reason": reason,
            "listings_cancelled": len(listing_ids),
            "reservations_cancelled": reservations,
        },
    )
    return DeactivationResult(store, len(listing_ids), reservations)


@transaction.atomic
def reactivate_store(store_id: UUID, admin: Any, reason: str) -> Store:
    """Let a deactivated store post again; cancelled listings stay cancelled."""
    from modules.audit import services as audit_services

    store = _locked_for_status_change(store_id, admin, activate=True)
    reason = _status_reason(reason)
    store.is_active = True
    store.save(update_fields=["is_active", "updated_at"])
    audit_services.record(admin, "reactivate", "store", store.pk, {"reason": reason})
    return store
