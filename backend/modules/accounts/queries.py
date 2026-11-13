# AI contribution: 50% or more AI-generated
"""Public role groups and account permission checks."""

import re
from hashlib import sha256

from django.utils import timezone

from modules.accounts.roles import UserRole

STORE_ROLES = (UserRole.STORE_STAFF, UserRole.STORE_MANAGER)
STAFF_ROLES = (UserRole.INTAKE_WORKER, UserRole.ADMIN)


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
