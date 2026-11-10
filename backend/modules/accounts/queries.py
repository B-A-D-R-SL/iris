# AI contribution: 50% or more AI-generated
"""Public role groups and account permission checks."""

from modules.accounts.roles import UserRole

STORE_ROLES = (UserRole.STORE_STAFF, UserRole.STORE_MANAGER)
STAFF_ROLES = (UserRole.INTAKE_WORKER, UserRole.ADMIN)


def is_admin(user: object) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
        and getattr(user, "role", None) == UserRole.ADMIN
    )
