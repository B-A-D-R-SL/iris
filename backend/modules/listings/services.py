# AI contribution: 50% or more AI-generated
"""Transactional posting; owning modules supply all cross-module reads."""

import logging
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime
from functools import partial
from importlib import import_module
from typing import Any, cast
from uuid import UUID

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import connection, transaction
from django.db.models import F
from django.utils import dateformat, timezone
from django.utils.translation import gettext_lazy as _

from adapters.photo_types import PhotoStorageError
from adapters.photos import PhotoValidationError
from modules.categories import queries as category_queries
from modules.listings.contracts import ListingPhotoStore, SafetyChecker
from modules.listings.domain.posting import (
    ListingInput,
    PostingLimits,
    Refusal,
    SafetyRulesInvalid,
    check_posting,
    safety_payload,
)
from modules.listings.models import Listing, ListingStatus
from modules.listings.permissions import assigned_store_id
from modules.listings.photo_storage import load_store
from modules.rules import queries as rule_queries
from modules.stores import queries as store_queries

logger = logging.getLogger("iris.listings")

PHOTO_SIGNATURES = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}

MESSAGES = {
    "title_length": _(
        "Enter a title of %(title_min_length)s to %(title_max_length)s characters."
    ),
    "description_length": _("Enter at most %(description_max_length)s characters."),
    "quantity_range": _("Enter a quantity from 1 to %(quantity_max)s."),
    "unit_choice": _("Choose item or bundle."),
    "household_range": _("Enter a household limit from 1 to %(max_per_household)s."),
    "value_range": _("Enter a value from 0 to %(estimated_value_max_cents)s cents."),
    "confirmation_required": _("Tick this box to publish."),
    "timezone_required": _("Include a timezone offset in the pickup time."),
    "pickup_start_range": _(
        "Choose a pickup start between now and %(pickup_start_max_days)s days ahead."
    ),
    "pickup_duration": _(
        "The pickup must last %(pickup_min_minutes)s to %(pickup_max_minutes)s minutes."
    ),
    "unsafe_listing": _("This listing was refused by the safety checks."),
    # US-34 safety refusals (forms-and-fields.md, "Listing form").
    "category_prohibited": _("This category can't be posted. Choose another one."),
    "best_before_required": _("Enter a best-before date. It is required for food."),
    "best_before_too_early": _("Choose %(date)s or later (end of pickup)."),
}

# Short month, as in the S1 mockup: "Oct. 10, 2026" / "10 oct. 2026".
DATE_DISPLAY_FORMAT = _("N j, Y")


def release_units(listing_id: UUID, quantity: int) -> None:
    """Return reserved units inside the caller's transaction."""
    if not connection.in_atomic_block:
        raise RuntimeError("release_units must run inside a transaction.")
    if quantity < 1:
        raise ValueError("quantity must be 1 or more.")
    changed = Listing.objects.filter(
        pk=listing_id, quantity_reserved__gte=quantity
    ).update(quantity_reserved=F("quantity_reserved") - quantity)
    if changed != 1:
        raise RuntimeError("Reserved listing units are inconsistent.")


class PostingUnavailableError(Exception):
    """A dependency failed; the reason is diagnostic and never user-facing."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(str(_("Posting is temporarily unavailable.")))


REFUSAL_CODES = frozenset(MESSAGES) | {
    "category_inactive",
    "photo_type",
    "photo_size",
    "photo_invalid",
    "listing_validation_failed",
    "store_access_denied",
}


def log_posting_unavailable(reason: str) -> None:
    """Use a static reason for service and posting-form dependency failures."""
    logger.error(
        "listing_posting_unavailable",
        extra={"event": "listing_posting_unavailable", "reason": reason},
    )


def log_post_refused(reason: str) -> None:
    """Record a registered reason for API or service validation failures."""
    logger.warning(
        "listing_post_refused",
        extra={
            "event": "listing_post_refused",
            "reason": reason
            if reason in REFUSAL_CODES
            else "listing_validation_failed",
        },
    )


def _log_post_failure(exc: Exception) -> None:
    """Log only registered codes, never translated validation messages."""
    if isinstance(exc, PostingUnavailableError):
        log_posting_unavailable(exc.reason)
    elif isinstance(exc, PermissionDenied):
        log_post_refused("store_access_denied")
    elif isinstance(exc, ValidationError):
        errors = (
            [error for group in exc.error_dict.values() for error in group]
            if hasattr(exc, "error_dict")
            else exc.error_list
        )
        reasons = {
            error.code if error.code in REFUSAL_CODES else "listing_validation_failed"
            for error in errors
        }
        for reason in sorted(reasons):
            log_post_refused(reason)


def _log_published(listing_id: UUID, store_id: UUID) -> None:
    """Emit a success only after the surrounding transaction commits."""
    logger.info(
        "listing_published",
        extra={
            "event": "listing_published",
            "listing_id": listing_id,
            "store_id": store_id,
        },
    )


def _display(value: Any) -> Any:
    """Format a refusal parameter for the user's language."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return dateformat.format(value, str(DATE_DISPLAY_FORMAT))
    return value


def _refuse(reasons: Sequence[Refusal], limits: PostingLimits) -> None:
    errors: dict[str, list[ValidationError]] = defaultdict(list)
    for reason in reasons:
        if not isinstance(reason, Refusal) or reason.code not in MESSAGES:
            raise PostingUnavailableError("safety_contract_invalid")
        values = vars(limits) | {
            key: _display(value) for key, value in reason.params.items()
        }
        errors[reason.field].append(
            ValidationError(str(MESSAGES[reason.code]) % values, code=reason.code)
        )
    if errors:
        raise ValidationError(dict(errors))


def _safety_checker() -> SafetyChecker:
    """Load US-34 when available; never substitute a passing checker in production."""
    try:
        module = import_module("modules.listings.domain.safety")
    except ModuleNotFoundError as exc:
        if exc.name != "modules.listings.domain.safety":
            raise
        raise PostingUnavailableError("safety_checker_missing") from None
    checker = getattr(module, "check", None)
    if not callable(checker):
        raise PostingUnavailableError("safety_contract_invalid")
    return cast(SafetyChecker, checker)


def _photo_store() -> ListingPhotoStore:
    if not settings.LISTING_PHOTO_STORE_BACKEND:
        raise PostingUnavailableError("photo_store_unconfigured")
    try:
        return load_store()
    except PhotoStorageError as exc:
        logger.error(
            "listing_photo_store_failed",
            extra={"event": "listing_photo_store_failed", "exc_type": type(exc)},
        )
        raise PostingUnavailableError("photo_store_failed") from None


def _posting_inputs(
    store: UUID,
    data: ListingInput,
    safety_check: SafetyChecker | None,
) -> tuple[dict[str, Any], PostingLimits, datetime]:
    offering_store = store_queries.for_listing_post(store)
    if offering_store is None or not offering_store.is_active:
        raise PermissionDenied(_("Your store must be active to post a listing."))
    category = category_queries.for_listing_post(data.category)
    if category is None or not category["is_active"]:
        raise ValidationError(
            {
                "category": ValidationError(
                    _("Choose an active category."), code="category_inactive"
                )
            }
        )
    now = timezone.now()
    posting_rules = rule_queries.active("listing_posting", at=now)
    safety_rules = rule_queries.active("listing_safety", at=now)
    if posting_rules is None or safety_rules is None:
        raise PostingUnavailableError("listing_rules_missing")
    try:
        limits = PostingLimits(**posting_rules.values)
    except TypeError:
        raise PostingUnavailableError("posting_rules_invalid") from None
    _refuse(check_posting(data, limits, now=now), limits)
    checker = safety_check if safety_check is not None else _safety_checker()
    listing_data = safety_payload(data, local_tz=timezone.get_default_timezone())
    try:
        reasons = checker(listing_data, category, safety_rules.values)
    except SafetyRulesInvalid:
        raise PostingUnavailableError("safety_rules_invalid") from None
    _refuse(reasons, limits)
    return category, limits, now


def _new_listing(
    store: UUID,
    user: AbstractBaseUser,
    data: ListingInput,
    category: dict[str, Any],
    now: datetime,
) -> Listing:
    listing = Listing(
        store_id=store,
        category_id=category["id"],
        title=data.title.strip(),
        description=data.description,
        quantity_total=data.quantity,
        unit=data.unit,
        max_per_household=data.max_per_household,
        pickup_start=data.pickup_start,
        pickup_end=data.pickup_end,
        best_before=data.best_before,
        estimated_value_cents=data.estimated_value_cents,
        status=ListingStatus.PUBLISHED,
        created_by_id=user.pk,
        safe_confirmed_by_id=user.pk,
        safe_confirmed_at=now,
        published_at=now,
    )
    listing.full_clean()
    return listing


def _photo_content(photo: UploadedFile, limits: PostingLimits) -> bytes:
    signature = PHOTO_SIGNATURES.get(photo.content_type or "")
    if signature is None:
        raise ValidationError(
            {
                "photo": ValidationError(
                    _("Choose a JPEG or PNG image."), code="photo_type"
                )
            }
        )
    content = photo.read(limits.photo_max_bytes + 1)
    if len(content) > limits.photo_max_bytes:
        raise ValidationError(
            {
                "photo": ValidationError(
                    _("The image exceeds the allowed file size."), code="photo_size"
                )
            }
        )
    if not content.startswith(signature):
        raise ValidationError(
            {
                "photo": ValidationError(
                    _("Choose a JPEG or PNG image."), code="photo_type"
                )
            }
        )
    return content


def _store_photo(
    photo: UploadedFile,
    limits: PostingLimits,
    file_store: ListingPhotoStore | None,
) -> tuple[str, ListingPhotoStore]:
    content = _photo_content(photo, limits)
    storage = file_store if file_store is not None else _photo_store()
    try:
        reference = storage.put_image(
            content,
            max_dimension=limits.photo_max_dimension,
            max_bytes=limits.photo_max_bytes,
        )
    except PhotoValidationError:
        raise ValidationError(
            {
                "photo": ValidationError(
                    _(
                        "Choose a readable still JPEG or PNG image within the allowed dimensions."
                    ),
                    code="photo_invalid",
                )
            }
        ) from None
    except PhotoStorageError as exc:
        logger.error(
            "listing_photo_store_failed",
            extra={"event": "listing_photo_store_failed", "exc_type": type(exc)},
        )
        raise PostingUnavailableError("photo_store_failed") from None
    return reference, storage


def _cleanup_photo(reference: str | None, storage: ListingPhotoStore | None) -> None:
    if reference is None or storage is None:
        return
    try:
        storage.delete(reference)
    except Exception:  # noqa: BLE001 - cleanup must preserve the original posting error.
        logger.error(
            "listing_photo_cleanup_failed",
            extra={"event": "listing_photo_cleanup_failed", "photo_ref": reference},
        )


def post_listing(
    store: UUID,
    user: AbstractBaseUser,
    data: ListingInput,
    *,
    photo: UploadedFile | None = None,
    safety_check: SafetyChecker | None = None,
    file_store: ListingPhotoStore | None = None,
) -> Listing:
    """Publish for the assigned store; injected dependencies are trusted test hooks."""
    photo_ref: str | None = None
    storage: ListingPhotoStore | None = None
    try:
        if assigned_store_id(user) != store:
            raise PermissionDenied(_("You can only post for your own store."))
        with transaction.atomic():
            category, limits, now = _posting_inputs(store, data, safety_check)
            listing = _new_listing(store, user, data, category, now)
            if photo is not None:
                photo_ref, storage = _store_photo(photo, limits, file_store)
                listing.photo_ref = photo_ref
                listing.full_clean()
            listing.save()
            transaction.on_commit(
                partial(_log_published, listing.pk, store), robust=True
            )
    except Exception as exc:
        _cleanup_photo(photo_ref, storage)
        _log_post_failure(exc)
        raise
    return listing
