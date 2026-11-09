# AI contribution: 50% or more AI-generated
"""Reserve a unit (US-41): POST /api/reservations/.

Thin: check the role and the household, validate the body, call
``services.reserve`` and turn a refusal into a status and a fixed, translated
message. The household always comes from the signed-in user, never from the
request, so no one can reserve as another household.
"""

from typing import Any

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler

from modules.reservations import services
from modules.reservations.api.permissions import IsBeneficiary, approved_household_id
from modules.reservations.api.reserve_serializers import (
    ReservationSerializer,
    ReserveInputSerializer,
)
from modules.reservations.api.serializers import BrowseErrorSerializer

NOT_APPROVED = _("Only approved households can reserve.")
CHECK_FIELDS = _("Check the highlighted fields.")
TRY_AGAIN = _("Reserving is not available right now. Try again later.")

# Each refusal: (HTTP status, message). Messages are fixed, never an
# exception's own text.
REFUSALS = {
    services.HOUSEHOLD_NOT_APPROVED: (status.HTTP_403_FORBIDDEN, NOT_APPROVED),
    services.LISTING_NOT_AVAILABLE: (
        status.HTTP_404_NOT_FOUND,
        _("This listing is no longer available."),
    ),
    services.SOLD_OUT: (
        status.HTTP_409_CONFLICT,
        _("Sorry, this listing is sold out."),
    ),
    services.NOT_ENOUGH_UNITS: (
        status.HTTP_409_CONFLICT,
        _("There are not enough left. Choose a smaller quantity."),
    ),
    services.QUANTITY_OVER_LISTING_LIMIT: (
        status.HTTP_400_BAD_REQUEST,
        _("That is more than one household can reserve for this listing."),
    ),
    services.TOO_MANY_ACTIVE_RESERVATIONS: (
        status.HTTP_409_CONFLICT,
        _(
            "You already have the most reservations allowed at one time. "
            "Pick one up or cancel one first."
        ),
    ),
    services.RESERVATIONS_UNAVAILABLE: (status.HTTP_503_SERVICE_UNAVAILABLE, TRY_AGAIN),
    services.PICKUP_CODE_UNAVAILABLE: (status.HTTP_503_SERVICE_UNAVAILABLE, TRY_AGAIN),
}
STATUS_MESSAGES = {
    status.HTTP_401_UNAUTHORIZED: _("Sign in to reserve."),
    status.HTTP_403_FORBIDDEN: NOT_APPROVED,
    status.HTTP_405_METHOD_NOT_ALLOWED: _("Reservations can only be made here."),
}
FIELD_MESSAGES = {
    "listing_id": _("Enter a valid listing ID."),
    "quantity": _("Enter a quantity from 1 to 10."),
}


def _error(
    code: str, message: Any, fields: dict[str, list[str]] | None = None
) -> dict[str, Any]:
    """The API's error shape: { code, message, fields }."""
    return {"code": code, "message": str(message), "fields": fields or {}}


def reserve_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Errors as { code, message, fields }, using fixed, translated messages."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data if isinstance(response.data, dict) else {}
    if isinstance(exc, ValidationError):
        names = list(data) or ["non_field_errors"]
        response.data = _error(
            "validation_error",
            CHECK_FIELDS,
            {name: [str(FIELD_MESSAGES.get(name, CHECK_FIELDS))] for name in names},
        )
    else:
        response.data = _error(
            getattr(data.get("detail"), "code", None) or "request_refused",
            STATUS_MESSAGES.get(response.status_code, _("The request was refused.")),
        )
    return response


@extend_schema_view(
    post=extend_schema(
        operation_id="reservations_create",
        summary="Reserve units of a listing for the signed-in household",
        tags=["reservations"],
        request=ReserveInputSerializer,
        responses={
            201: ReservationSerializer,
            400: BrowseErrorSerializer,
            401: BrowseErrorSerializer,
            403: BrowseErrorSerializer,
            404: BrowseErrorSerializer,
            409: BrowseErrorSerializer,
            503: BrowseErrorSerializer,
        },
    )
)
class ReserveView(APIView):
    """Reserve in one tap; the reply carries the pickup code."""

    permission_classes = (IsBeneficiary,)
    http_method_names = ("post", "options")

    def get_exception_handler(self) -> Any:
        """Use the { code, message, fields } error shape for this view."""
        return reserve_exception_handler

    def post(self, request: Request) -> Response:
        """Validate, reserve, and answer 201 with the code or a refusal."""
        now = timezone.now()
        household_id = approved_household_id(request.user, at=now)
        body = ReserveInputSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            reservation = services.reserve(
                request.user,
                household_id,
                body.validated_data["listing_id"],
                body.validated_data["quantity"],
                now=now,
            )
        except services.ReservationRefused as refused:
            http_status, message = REFUSALS[refused.code]
            return Response(_error(refused.code, message), status=http_status)
        return Response(
            ReservationSerializer(reservation).data, status=status.HTTP_201_CREATED
        )
