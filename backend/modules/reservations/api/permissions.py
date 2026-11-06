# AI contribution: 50% or more AI-generated
"""Who may browse listings: an active beneficiary whose household is approved."""

from datetime import datetime
from typing import Any
from uuid import UUID

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from modules.households import queries as household_queries

BENEFICIARY_ROLE = "beneficiary"
NOT_APPROVED = _("Only approved households can see listings.")


class HouseholdNotApproved(PermissionDenied):
    """HTTP 403 with its own code, so the screen can explain why."""

    default_code = "household_not_approved"
    default_detail = NOT_APPROVED


class IsBeneficiary(BasePermission):
    """Deny by default: only an active beneficiary account passes.

    Staff browse on a household's behalf through their own endpoints (US-47).
    """

    message = NOT_APPROVED

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            getattr(user, "is_authenticated", False)
            and getattr(user, "is_active", False)
            and getattr(user, "role", None) == BENEFICIARY_ROLE
        )


def approved_household_id(user: Any, *, at: datetime) -> UUID:
    """The ID of the user's approved household, or HTTP 403 (US-36)."""
    household_id = household_queries.approved_household_id(user.pk, at=at)
    if household_id is None:
        raise HouseholdNotApproved()
    return household_id
