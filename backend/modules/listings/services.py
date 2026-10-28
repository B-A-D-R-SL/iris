# AI contribution: 50% or more AI-generated
"""Transactional posting; owning modules supply all cross-module reads."""

import logging
from collections import defaultdict
from collections.abc import Sequence
from importlib import import_module
from typing import cast
from uuid import UUID

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from modules.categories import queries as category_queries
from modules.listings.contracts import ListingPhotoStore, SafetyChecker
from modules.listings.domain.posting import (
    ListingInput,
    PostingLimits,
    Refusal,
    check_posting,
    safety_payload,
)
from modules.listings.models import Listing, ListingStatus
from modules.listings.permissions import assigned_store_id
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
}


class PostingUnavailable(Exception):
    """A required integration or rule version has not been configured."""


def _refuse(reasons: Sequence[Refusal], limits: PostingLimits) -> None:
    errors: dict[str, list[str]] = defaultdict(list)
    for reason in reasons:
        if not isinstance(reason, Refusal) or reason.code not in MESSAGES:
            raise PostingUnavailable(
                _("The listing safety integration needs configuration.")
            )
        errors[reason.field].append(str(MESSAGES[reason.code]) % vars(limits))
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
    backend = getattr(settings, "LISTING_PHOTO_STORE_BACKEND", "")
    if not backend:
        raise PostingUnavailable(_("Listing photo storage is not available yet."))
    return cast(ListingPhotoStore, import_string(backend)())


def post_listing(
    store: UUID,
    user: AbstractBaseUser,
    data: ListingInput,
    *,
    photo: UploadedFile | None = None,
    safety_check: SafetyChecker | None = None,
    file_store: ListingPhotoStore | None = None,
) -> Listing:
    """Post for the user's assigned active store, or leave no listing behind.

    Checker/storage injection is for trusted service callers and unit tests;
    the HTTP endpoint never accepts either dependency from request data.
    """
    if assigned_store_id(user) != store:
        raise PermissionDenied(_("You can only post for your own store."))

    photo_ref: str | None = None
    storage: ListingPhotoStore | None = None
    try:
        with transaction.atomic():
            offering_store = store_queries.for_listing_post(store)
            if offering_store is None or not offering_store.is_active:
                raise PermissionDenied(
                    _("Your store must be active to post a listing.")
                )

            category = category_queries.for_listing_post(data.category)
            if category is None or not category["is_active"]:
                raise ValidationError({"category": _("Choose an active category.")})

            now = timezone.now()
            posting_rules = rule_queries.active("listing_posting", at=now)
            safety_rules = rule_queries.active("listing_safety", at=now)
            if posting_rules is None or safety_rules is None:
                raise PostingUnavailable(
                    _("Listing rules must be seeded before posting.")
                )
            try:
                limits = PostingLimits(**posting_rules.values)
            except TypeError as exc:
                raise PostingUnavailable(
                    _("Listing posting rules need configuration.")
                ) from exc
            _refuse(check_posting(data, limits, now=now), limits)
            checker = safety_check if safety_check is not None else _safety_checker()
            _refuse(
                checker(safety_payload(data), category, safety_rules.values), limits
            )

            listing = Listing(
                store_id=store,
                category_id=data.category,
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
            if photo is not None:
                signature = PHOTO_SIGNATURES.get(photo.content_type or "")
                if signature is None:
                    raise ValidationError({"photo": _("Choose a JPEG or PNG image.")})
                content = photo.read(limits.photo_max_bytes + 1)
                if len(content) > limits.photo_max_bytes:
                    raise ValidationError(
                        {"photo": _("The image exceeds the allowed file size.")}
                    )
                if not content.startswith(signature):
                    raise ValidationError({"photo": _("Choose a JPEG or PNG image.")})
                storage = file_store if file_store is not None else _photo_store()
                photo_ref = storage.put_image(
                    content, max_dimension=limits.photo_max_dimension
                )
                listing.photo_ref = photo_ref
                listing.full_clean()
            listing.save()
            return listing
    except Exception:
        if photo_ref is not None and storage is not None:
            try:
                storage.delete(photo_ref)
            except Exception:  # noqa: BLE001 - preserve the original posting error.
                # No filenames, references, user data or provider error text.
                logger.error("listing_photo_cleanup_failed")
        raise
