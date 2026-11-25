# AI contribution: 50% or more AI-generated
"""Public account invitation operations with atomic, single-use acceptance."""

import logging
import re
import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import UUID

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.dispatch import Signal
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.accounts import queries
from modules.accounts.models import Invitation, User
from modules.accounts.roles import UserRole
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.accounts")

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_EMAIL_UNIQUE_CONSTRAINTS = frozenset(
    ("accounts_user_email_key", "accounts_user_email_ci_unique")
)

# US-93: sent inside the acceptance transaction with `user` and `household_id`
# when the invitation names a household. Households links the account; a
# receiver that raises rolls the whole acceptance back. Accounts never imports
# households (import-linter), so the link travels through this signal.
invitation_accepted = Signal()

# US-08: sent inside the caller's transaction with `user` and `language` after a
# user's language is saved. Households keeps the holder's file in the same
# language, so the household's emails follow the account too.
language_changed = Signal()

LANGUAGES = frozenset(code for code, _label in settings.LANGUAGES)


def _identity_text(value: str, field: str) -> str:
    """Keep service inputs predictable before Django validates model fields."""
    if not isinstance(value, str):
        raise ValidationError({field: _("Enter a valid value.")})
    return value.strip()


def _require_new_email(email: str) -> None:
    """An invitation can never reset or reactivate an existing account."""
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError(
            _("An account already uses this email address."),
            code="email_already_registered",
        )


def _invitation_expiry(now: datetime) -> datetime:
    """Resolve the active lifetime without inventing a fallback configuration."""
    rule = rule_queries.active("invitations", at=now)
    days = (
        rule.values.get("expires_after_days")
        if rule and isinstance(rule.values, dict)
        else None
    )
    if type(days) is not int or days < 1:
        raise ValidationError(
            _("Invitations are temporarily unavailable. Try again later."),
            code="invitation_unavailable",
        )
    try:
        return now + timedelta(days=days)
    except OverflowError as exc:
        raise ValidationError(
            _("Invitations are temporarily unavailable. Try again later."),
            code="invitation_unavailable",
        ) from exc


def create_invitation(
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    store: Any = None,
    invited_by: User | None = None,
    household_id: UUID | None = None,
) -> str:
    """Save a recipient assignment and return the raw token only to the caller.

    `household_id` names the walk-in file the accepted account will hold (US-93).
    """
    email = User.objects.normalize_email(_identity_text(email, "email")).lower()
    _require_new_email(email)
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        email=email,
        first_name=_identity_text(first_name, "first_name"),
        last_name=_identity_text(last_name, "last_name"),
        role=role,
        store=store,
        invited_by=invited_by,
        household_id=household_id,
        token_hash=sha256(token.encode("utf-8")).hexdigest(),
        expires_at=_invitation_expiry(timezone.now()),
    )
    invitation.full_clean()
    invitation.save()
    transaction.on_commit(
        lambda: logger.info("invitation_created", extra={"event": "invitation_created"})
    )
    return token


@transaction.atomic
def reissue_store_manager_invitation(
    *, email: str, first_name: str, last_name: str, store: Any, invited_by: User
) -> str:
    """Expire previous links under lock, then issue a fresh manager invitation.

    The calling stores service locks the application to serialize reissues.
    Locking invitations also serializes against concurrent acceptance. A failed
    issuance rolls back expiry changes, preserving the previous usable link.
    """
    if not invited_by.is_active or invited_by.role != UserRole.ADMIN:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied(_("An active admin is required."))
    previous = list(
        Invitation.objects.select_for_update().filter(
            store=store, email__iexact=email, role=UserRole.STORE_MANAGER
        )
    )
    if not previous or any(item.accepted_at is not None for item in previous):
        raise ValidationError(
            _("No unaccepted store-manager invitation exists."),
            code="invitation_not_pending",
        )
    Invitation.objects.filter(pk__in=[item.pk for item in previous]).update(
        expires_at=timezone.now()
    )
    return create_invitation(
        email, first_name, last_name, UserRole.STORE_MANAGER, store, invited_by
    )


def lock_household_invitations(household_id: UUID) -> None:
    """Lock a household's unaccepted invitations for the caller's transaction.

    Acceptance locks the invitation, then the household (US-93). A caller about
    to lock the household and then expire its links calls this first, so both
    take the same order and wait for each other instead of deadlocking.
    """
    list(
        Invitation.objects.select_for_update()
        .filter(household_id=household_id, accepted_at__isnull=True)
        .values_list("pk", flat=True)
    )


@transaction.atomic
def reissue_household_invitation(
    *,
    household_id: UUID,
    email: str,
    first_name: str,
    last_name: str,
    invited_by: User,
) -> str:
    """Expire a walk-in household's earlier links, then issue a fresh one (US-93).

    Also expires unaccepted beneficiary links for the same email that name no
    household: they were sent before invitations named their household. Raises
    email_already_registered when the email now has an account; the earlier
    links then stay usable because the transaction rolls back.
    """
    if not queries.is_intake_staff(invited_by):
        raise PermissionDenied(_("Only active intake workers and admins can invite."))
    now = timezone.now()
    # The caller locks the household's links first (lock_household_invitations).
    Invitation.objects.filter(
        Q(household_id=household_id)
        | Q(household__isnull=True, email__iexact=email, role=UserRole.BENEFICIARY),
        accepted_at__isnull=True,
        expires_at__gt=now,
    ).update(expires_at=now)
    return create_invitation(
        email,
        first_name,
        last_name,
        UserRole.BENEFICIARY,
        invited_by=invited_by,
        household_id=household_id,
    )


def _locked_invitation(token: str) -> Invitation:
    """Resolve only correctly shaped URL-safe tokens while holding the row lock."""
    if not isinstance(token, str) or not _TOKEN_PATTERN.fullmatch(token):
        raise ValidationError(
            _("This invitation link is invalid."), code="invitation_invalid"
        )
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    invitation = (
        Invitation.objects.select_for_update().filter(token_hash=token_hash).first()
    )
    if invitation is None:
        raise ValidationError(
            _("This invitation link is invalid."), code="invitation_invalid"
        )
    return invitation


def _create_invited_user(invitation: Invitation, password: str) -> User:
    """Validate against recipient attributes, then rely on database email uniqueness."""
    values: dict[str, Any] = {
        "email": invitation.email,
        "first_name": invitation.first_name,
        "last_name": invitation.last_name,
        "role": invitation.role,
        "store_id": invitation.store_id,
        "is_active": True,
    }
    if not isinstance(password, str) or not password.strip():
        raise ValidationError(
            {"password": ValidationError(_("Enter a password."), code="required")}
        )
    try:
        validate_password(password, user=User(**values))
    except ValidationError as exc:
        raise ValidationError({"password": exc.error_list}) from exc
    try:
        with transaction.atomic():
            return User.objects.create_user(password=password, **values)
    except IntegrityError as exc:
        diagnostic = getattr(exc.__cause__, "diag", None)
        if (
            getattr(diagnostic, "constraint_name", None)
            not in _EMAIL_UNIQUE_CONSTRAINTS
        ):
            raise
        raise ValidationError(
            _("An account already uses this email address."),
            code="email_already_registered",
        ) from exc


@transaction.atomic
def accept_invitation(token: str, password: str) -> User:
    """Create the new account and consume the token in one locked transaction."""
    invitation = _locked_invitation(token)
    if invitation.accepted_at is not None:
        raise ValidationError(
            _("This invitation link has already been used."), code="invitation_used"
        )
    now = timezone.now()
    if invitation.expires_at <= now:
        raise ValidationError(
            _("This invitation link has expired."), code="invitation_expired"
        )
    _require_new_email(invitation.email)
    user = _create_invited_user(invitation, password)
    invitation.accepted_at = now
    invitation.save(update_fields=["accepted_at"])
    if invitation.household_id is not None:
        invitation_accepted.send(
            sender=Invitation, user=user, household_id=invitation.household_id
        )
    transaction.on_commit(
        lambda: logger.info(
            "invitation_accepted", extra={"event": "invitation_accepted"}
        )
    )
    return user


@transaction.atomic
def change_language(user: User, language: str) -> User:
    """Save the user's interface and email language (US-08).

    Every later email to the user, and to the household file they hold, uses it.
    `language_changed` is sent even when the value is unchanged, so a household
    file that drifted (for example linked at the counter) is brought back in step.
    """
    if language not in LANGUAGES:
        raise ValidationError(_("Choose French or English."), code="invalid_language")
    if user.preferred_language != language:
        user.preferred_language = language
        user.save(update_fields=["preferred_language", "updated_at"])
    language_changed.send(sender=User, user=user, language=language)
    transaction.on_commit(
        lambda: logger.info("language_changed", extra={"event": "language_changed"})
    )
    return user
