# AI contribution: 50% or more AI-generated
"""HTTP permission for the store pickup endpoints; the queries and service recheck it."""

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from modules.reservations.permissions import pickup_store_id


class IsPickupStaff(BasePermission):
    """Deny by default: only active store staff or managers with a store pass."""

    message = _("An active store account is required to confirm pickups.")

    def has_permission(self, request: Request, view: APIView) -> bool:
        """True only when the account is assigned to a store (BR-RES-001)."""
        try:
            pickup_store_id(request.user)
        except PermissionDenied:
            return False
        return True
