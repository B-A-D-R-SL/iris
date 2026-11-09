# AI contribution: 50% or more AI-generated
"""Public account invitation creation."""

import logging
import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from modules.accounts.models import Invitation, User
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.accounts")


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
