# AI contribution: 50% or more AI-generated
"""Shared HTTP security boundaries, independent of business module services."""

from typing import Any

from rest_framework.exceptions import Throttled
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class IsActiveAdmin(BasePermission):
    """Documentation is infrastructure; only the active Iris admin role may read it."""

    def has_permission(self, request: Request, view: Any) -> bool:
        """Use the application role rather than Django's separate admin-site flag."""
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and getattr(user, "role", None) == "admin"
        )


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Adapt only throttle refusals, preserving DRF's status and Retry-After header."""
    response = drf_exception_handler(exc, context)
    if response is not None and isinstance(exc, Throttled):
        response.data = {
            "code": "throttled",
            # DRF supplies this fixed message and its French/English catalogs.
            # Arbitrary exception detail is never exposed by this shared handler.
            "message": str(Throttled.default_detail),
            "fields": {},
        }
    return response
