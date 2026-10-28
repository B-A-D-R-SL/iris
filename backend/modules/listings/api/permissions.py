# AI contribution: 50% or more AI-generated
"""HTTP permission boundary; the service rechecks the same ownership rule."""

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from modules.listings.permissions import assigned_store_id


class IsStorePoster(BasePermission):
    message = _("An active store account is required to post a listing.")

    def has_permission(self, request: Request, view: APIView) -> bool:
        try:
            assigned_store_id(request.user)
        except PermissionDenied:
            return False
        return True
