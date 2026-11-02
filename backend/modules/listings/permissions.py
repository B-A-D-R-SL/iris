# AI contribution: 50% or more AI-generated
"""Store ownership checks using US-01's public user attributes."""

from typing import Any
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

POSTING_ROLES = frozenset({"store_staff", "store_manager"})


def assigned_store_id(user: Any) -> UUID:
    """Deny accounts without a real role/store assignment; is_staff is unrelated."""
    store_id = getattr(user, "store_id", None)
    if (
        not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
        or getattr(user, "role", None) not in POSTING_ROLES
        or not isinstance(store_id, UUID)
    ):
        raise PermissionDenied(
            _("An active store account is required to post a listing.")
        )
    return store_id
