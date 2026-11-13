# AI contribution: 50% or more AI-generated
"""Who may look up and confirm pickups: staff of an active store account."""

from typing import Any
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

PICKUP_ROLES = frozenset({"store_staff", "store_manager"})


def pickup_store_id(user: Any) -> UUID:
    """The store whose pickups ``user`` may confirm; deny everyone else (BR-RES-001)."""
    store_id = getattr(user, "store_id", None)
    if (
        not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
        or getattr(user, "role", None) not in PICKUP_ROLES
        or not isinstance(store_id, UUID)
    ):
        raise PermissionDenied(
            _("An active store account is required to confirm pickups.")
        )
    return store_id
