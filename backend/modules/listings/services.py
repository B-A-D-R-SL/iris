# AI contribution: 50% or more AI-generated
"""Transactional posting, and taking units for reservations (US-41).

Owning modules supply all cross-module reads.
"""

import logging
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime
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


class PostingUnavailable(Exception):
    """A required integration or rule version has not been configured."""


def _display(value: Any) -> Any:
    """Format a refusal parameter for the user's language."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return dateformat.format(value, str(DATE_DISPLAY_FORMAT))
    return value


def _refuse(reasons: Sequence[Refusal], limits: PostingLimits) -> None:
    errors: dict[str, list[str]] = defaultdict(list)
    for reason in reasons:
        if not isinstance(reason, Refusal) or reason.code not in MESSAGES:
            raise PostingUnavailable(
                _("The listing safety integration needs configuration.")
            )
        values = vars(limits) | {
            key: _display(value) for key, value in reason.params.items()
        }
        errors[reason.field].append(str(MESSAGES[reason.code]) % values)
    if errors:
        raise ValidationError(dict(errors))


def _safety_checker() -> SafetyChecker:
    """Load US-34 when available; never substitute a passing checker in production."""
    try:
        module = import_module("modules.listings.domain.safety")
    except ModuleNotFoundError as exc:
        if exc.name != "modules.listings.domain.safety":
            raise
        raise PostingUnavailable(
            _("Listing safety checks are not available yet.")
        ) from exc
    checker = getattr(module, "check", None)
    if not callable(checker):
        raise PostingUnavailable(
            _("The listing safety integration needs configuration.")
        )
    return cast(SafetyChecker, checker)


def _photo_store() -> ListingPhotoStore:
    if not settings.LISTING_PHOTO_STORE_BACKEND:
        raise PostingUnavailable(_("Listing photo storage is not available yet."))
    try:
        return load_store()
    except PhotoStorageError:
        logger.error(
            "listing_photo_store_failed", extra={"event": "listing_photo_store_failed"}
        )
        raise PostingUnavailable(_("Posting is temporarily unavailable.")) from None


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
        raise ValidationError({"category": _("Choose an active category.")})
    now = timezone.now()
    posting_rules = rule_queries.active("listing_posting", at=now)
    safety_rules = rule_queries.active("listing_safety", at=now)
    if posting_rules is None or safety_rules is None:
        raise PostingUnavailable(_("Listing rules must be seeded before posting."))
    try:
        limits = PostingLimits(**posting_rules.values)
    except TypeError as exc:
        raise PostingUnavailable(
            _("Listing posting rules need configuration.")
        ) from exc
    _refuse(check_posting(data, limits, now=now), limits)
    checker = safety_check if safety_check is not None else _safety_checker()
    listing_data = safety_payload(data, local_tz=timezone.get_default_timezone())
    try:
        reasons = checker(listing_data, category, safety_rules.values)
    except SafetyRulesInvalid as exc:
        raise PostingUnavailable(_("Listing safety rules need configuration.")) from exc
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
        raise ValidationError({"photo": _("Choose a JPEG or PNG image.")})
    content = photo.read(limits.photo_max_bytes + 1)
    if len(content) > limits.photo_max_bytes:
        raise ValidationError({"photo": _("The image exceeds the allowed file size.")})
    if not content.startswith(signature):
        raise ValidationError({"photo": _("Choose a JPEG or PNG image.")})
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
                "photo": _(
                    "Choose a readable still JPEG or PNG image within the allowed dimensions."
                )
            }
        ) from None
    except PhotoStorageError:
        logger.error(
            "listing_photo_store_failed", extra={"event": "listing_photo_store_failed"}
        )
        raise PostingUnavailable(_("Posting is temporarily unavailable.")) from None
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
    if assigned_store_id(user) != store:
        raise PermissionDenied(_("You can only post for your own store."))

    photo_ref: str | None = None
    storage: ListingPhotoStore | None = None
    try:
        with transaction.atomic():
            category, limits, now = _posting_inputs(store, data, safety_check)
            listing = _new_listing(store, user, data, category, now)
            if photo is not None:
                photo_ref, storage = _store_photo(photo, limits, file_store)
                listing.photo_ref = photo_ref
                listing.full_clean()
            listing.save()
    except Exception:
        _cleanup_photo(photo_ref, storage)
        raise
    logger.info("listing_published", extra={"event": "listing_published"})
    return listing


def take_units(listing_id: UUID, quantity: int, *, now: datetime) -> bool:
    """Count ``quantity`` more units of a listing as reserved, if they are left.

    One conditional UPDATE does the check and the change together, so two
    reservations at the same moment can never both take the last unit: the
    database runs them one after the other on this row, and the second sees
    what the first left (US-41, BR-RES-009). Never read the counter, add to it
    in Python and save it back. Only a published listing whose pickup has not
    ended gives units. True when the units were taken, False otherwise.

    Must run inside the caller's transaction, so a failure after this call
    (the reservation insert) also gives the units back.
    """
    if not connection.in_atomic_block:
        raise RuntimeError("take_units must run inside the caller's transaction.")
    if quantity < 1:
        raise ValueError("quantity must be 1 or more.")
    if now.utcoffset() is None:
        raise ValueError("The supplied clock must be timezone-aware.")
    # rule: BR-RES-009 atomic, only while published and before the pickup ends.
    changed = Listing.objects.filter(
        pk=listing_id,
        status=ListingStatus.PUBLISHED,
        pickup_end__gt=now,
        quantity_total__gte=F("quantity_reserved") + quantity,
    ).update(quantity_reserved=F("quantity_reserved") + quantity)
    return changed == 1
