# AI contribution: 50% or more AI-generated
"""Public account invitation operations with atomic, single-use acceptance."""

import logging
import re
import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.accounts.models import Invitation, User
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.accounts")

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")
_EMAIL_UNIQUE_CONSTRAINTS = frozenset(
    ("accounts_user_email_key", "accounts_user_email_ci_unique")
)


def _identity_text(value: str, field: str) -> str:
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
) -> str:
    """Save a recipient assignment and return the raw token only to the caller."""
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
        token_hash=sha256(token.encode("utf-8")).hexdigest(),
        expires_at=_invitation_expiry(timezone.now()),
    )
    invitation.full_clean()
    invitation.save()
    transaction.on_commit(
        lambda: logger.info("invitation_created", extra={"event": "invitation_created"})
    )
    return token


def _locked_invitation(token: str) -> Invitation:
    """Hold the token row lock until acceptance commits."""
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
    """Database email uniqueness also protects competing invitations."""
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
    transaction.on_commit(
        lambda: logger.info(
            "invitation_accepted", extra={"event": "invitation_accepted"}
        )
    )
    return user
