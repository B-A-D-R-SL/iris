# AI contribution: 50% or more AI-generated
"""Public read-only interfaces for accounts."""

from modules.accounts.models import User

# Roles that manage walk-in household files and notices of assessment.
INTAKE_STAFF_ROLES = frozenset((User.Role.INTAKE_WORKER, User.Role.ADMIN))


def is_intake_staff(user: object) -> bool:
    """True for a signed-in, active intake worker or admin (deny by default)."""
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "role", None) in INTAKE_STAFF_ROLES
    )
