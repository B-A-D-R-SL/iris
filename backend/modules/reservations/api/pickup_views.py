# AI contribution: 50% or more AI-generated
"""Store pickup endpoints (US-44): a thin boundary over the lookup and confirm."""

from typing import Any
from uuid import UUID

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from modules.reservations import queries, services
from modules.reservations.api.pickup_serializers import (
    PickupErrorSerializer,
    PickupLookupSerializer,
    PickupSerializer,
)
from modules.reservations.api.store_permissions import IsPickupStaff
from modules.reservations.domain import pickup
from modules.reservations.domain.pickup import PickupRefused

# Fixed messages only: never the typed code or a household detail. The scan
# screen shows its own French or English text for each code.
REFUSALS = {
    pickup.UNKNOWN_CODE: (
        status.HTTP_404_NOT_FOUND,
        _(
            "No reservation at your store has this code. "
            "Check the characters or scan the QR code."
        ),
    ),
    pickup.UNKNOWN_RESERVATION: (
        status.HTTP_404_NOT_FOUND,
        _("This reservation is not at your store."),
    ),
    pickup.WRONG_STORE: (
        status.HTTP_409_CONFLICT,
        _(
            "This reservation is picked up somewhere else. The person can find "
            "the address in their email or under My reservations."
        ),
    ),
    pickup.AMBIGUOUS_CODE: (
        status.HTTP_409_CONFLICT,
        _(
            "Several reservations at your store use this code. "
            "Find the person in today's pickups instead."
        ),
    ),
    pickup.ALREADY_PICKED_UP: (
        status.HTTP_409_CONFLICT,
        _(
            "This reservation was already handed over. "
            "Do not hand over the items a second time."
        ),
    ),
    pickup.CANCELLED: (
        status.HTTP_409_CONFLICT,
        _(
            "This reservation was cancelled. "
            "The items are no longer held for this person."
        ),
    ),
    pickup.NO_SHOW: (
        status.HTTP_409_CONFLICT,
        _("This pickup was marked as missed and cannot be confirmed here."),
    ),
    pickup.NOT_OPEN_YET: (
        status.HTTP_409_CONFLICT,
        _(
            "This pickup has not started yet. "
            "Hand over the items once the pickup window opens."
        ),
    ),
    pickup.WINDOW_ENDED: (
        status.HTTP_409_CONFLICT,
        _("The pickup window has ended. This pickup cannot be confirmed here."),
    ),
}
ERROR_RESPONSES = {code: PickupErrorSerializer for code in (400, 401, 403, 404, 409)}


def pickup_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Every error as ``{code, message, fields}``, with fixed translated messages."""
    if isinstance(exc, PickupRefused):
        http_status, message = REFUSALS[exc.code]
        data: dict[str, Any] = {"code": exc.code, "message": str(message), "fields": {}}
        if exc.picked_up_at is not None:
            data["picked_up_at"] = exc.picked_up_at
        return Response(PickupErrorSerializer(data).data, status=http_status)
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        fields = response.data
        if not isinstance(fields, dict):
            fields = {"non_field_errors": fields}
        response.data = {
            "code": "validation_error",
            "message": str(_("Check the highlighted fields.")),
            "fields": {
                key: value if isinstance(value, list) else [value]
                for key, value in fields.items()
            },
        }
    else:
        response.data = {
            "code": getattr(exc, "default_code", "permission_denied"),
            "message": str(response.data.get("detail", _("The request was refused."))),
            "fields": {},
        }
    return response


class PickupView(GenericAPIView):
    permission_classes = (IsPickupStaff,)

    def get_exception_handler(self) -> Any:
        """Use the pickup error shape for both endpoints."""
        return pickup_exception_handler


class PickupLookupView(PickupView):
    serializer_class = PickupLookupSerializer

    @extend_schema(
        operation_id="store_pickups_lookup",
        summary="Find a reservation at the signed-in staff member's store by its code",
        tags=["store pickups"],
        responses={200: PickupSerializer, **ERROR_RESPONSES},
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Show who and what before confirming; changes nothing."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        found = queries.lookup_pickup(
            request.user, serializer.validated_data["code"], now=timezone.now()
        )
        return Response(PickupSerializer(found).data)


class PickupConfirmView(PickupView):
    serializer_class = PickupSerializer

    @extend_schema(
        operation_id="store_pickups_confirm",
        summary="Mark a reservation at the signed-in staff member's store picked up",
        tags=["store pickups"],
        request=None,
        responses={200: PickupSerializer, **ERROR_RESPONSES},
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        """One tap: record who confirmed and when, exactly once."""
        confirmed = services.confirm_pickup(id, request.user)
        return Response(PickupSerializer(confirmed).data)
