# AI contribution: 50% or more AI-generated
"""Public role groups and account permission checks."""

import re
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from django.utils import timezone

from modules.accounts.roles import UserRole

# Other modules may not import accounts.roles (import-linter), so they read
# UserRole and these groups from here.
STORE_ROLES = (UserRole.STORE_STAFF, UserRole.STORE_MANAGER)
STAFF_ROLES = (UserRole.INTAKE_WORKER, UserRole.ADMIN)
BENEFICIARY_ROLE = UserRole.BENEFICIARY


def is_admin(user: object) -> bool:
    """Return whether the user is an active authenticated administrator."""
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "role", None) == UserRole.ADMIN
    )


def is_intake_staff(user: object) -> bool:
    """Return whether the user is an active intake worker or administrator."""
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "role", None) in STAFF_ROLES
    )


@dataclass(frozen=True)
class AccountSummary:
    """What households may know about the account that uses a file's email."""

    id: UUID
    first_name: str
    last_name: str
    role: str
    is_active: bool


def account_for_email(email: str, *, lock: bool = False) -> AccountSummary | None:
    """The account using this email (case-insensitive), or None (US-93).

    With `lock`, the row stays locked until the caller's transaction ends, so
    the role and activation a caller checks cannot change before it commits.
    """
    from modules.accounts.models import User

    users = User.objects.select_for_update() if lock else User.objects
    row = (
        users.filter(email__iexact=email)
        .values("id", "first_name", "last_name", "role", "is_active")
        .first()
    )
    return AccountSummary(**row) if row else None


def invitation_is_usable(token: str, email: str) -> bool:
    """Check a queued link's recipient and current validity without exposing it.

    This is a preflight check, not a reservation: acceptance or reissue can still
    race a transport call already in progress. Accounts enforces validity again
    when the recipient attempts to accept the invitation.
    """
    from modules.accounts.models import Invitation, User

    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        return False
    return (
        Invitation.objects.filter(
            token_hash=sha256(token.encode("utf-8")).hexdigest(),
            email__iexact=email,
            expires_at__gt=timezone.now(),
            accepted_at__isnull=True,
        ).exists()
        and not User.objects.filter(email__iexact=email).exists()
    )
