# AI contribution: 50% or more AI-generated
"""HTTP endpoints for accounts."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from modules.accounts import services
from modules.accounts.api.serializers import (
    AcceptInvitationSerializer,
    CurrentUserSerializer,
    InvitationAcceptedSerializer,
    InvitationErrorSerializer,
)

_INVITATION_MESSAGES = {
    "invitation_invalid": _("This invitation link is invalid."),
    "invitation_expired": _("This invitation link has expired."),
    "invitation_used": _("This invitation link has already been used."),
    "email_already_registered": _("An account already uses this email address."),
    "invitation_unavailable": _(
        "Invitations are temporarily unavailable. Try again later."
    ),
}
_PASSWORD_MESSAGES = {
    "required": _("Enter a password."),
    "password_too_short": _("This password is too short."),
    "password_too_similar": _(
        "This password is too similar to your personal information."
    ),
    "password_too_common": _("This password is too common."),
    "password_entirely_numeric": _("This password is entirely numeric."),
}


@extend_schema(
    responses={
        200: CurrentUserSerializer,
        401: OpenApiResponse(description="Authentication required."),
    }
)
@api_view(["GET"])
def current_user(request: Request) -> Response:
    return Response(CurrentUserSerializer(request.user).data)


def _messages(value: Any) -> list[str]:
    """Flatten serializer field errors into the API's list-of-strings format."""
    if isinstance(value, dict):
        return [message for item in value.values() for message in _messages(item)]
    if isinstance(value, list):
        return [message for item in value for message in _messages(item)]
    return [str(value)]


def _password_message(error: DjangoValidationError) -> str:
    """Map approved codes, interpolating only Django's safe numeric length parameter."""
    code = getattr(error, "code", None)
    if code == "password_too_short":
        params = getattr(error, "params", None)
        minimum = params.get("min_length") if isinstance(params, dict) else None
        if type(minimum) is int and minimum > 0:
            return str(
                _("This password must contain at least %(min_length)s characters.")
                % {"min_length": minimum}
            )
    message = _PASSWORD_MESSAGES.get(code) if isinstance(code, str) else None
    return str(message or _("Enter a valid value."))


def _invitation_fields(exc: DjangoValidationError) -> dict[str, list[str]]:
    """Hide unknown service field names and never serialize exception message text."""
    fields: dict[str, list[str]] = {}
    for field, errors in getattr(exc, "error_dict", {}).items():
        if field == "password":
            fields[field] = [_password_message(error) for error in errors]
        else:
            fields["non_field_errors"] = [str(_("Enter a valid value."))]
    return fields


def _invitation_service_error(exc: DjangoValidationError) -> Response:
    """Return approved translated messages; arbitrary exception data stays private."""
    code = getattr(exc, "code", None)
    if not isinstance(code, str) or code not in _INVITATION_MESSAGES:
        code = "validation_error"
    fields = _invitation_fields(exc)
    return Response(
        {
            "code": code,
            "message": str(
                _INVITATION_MESSAGES.get(code, _("Check the highlighted fields."))
            ),
            "fields": fields,
        },
        status=503 if code == "invitation_unavailable" else 400,
    )


def invitation_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Use the same error envelope for service, input, CSRF and method failures."""
    if isinstance(exc, DjangoValidationError):
        return _invitation_service_error(exc)
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
            "fields": {key: _messages(value) for key, value in fields.items()},
        }
    else:
        response.data = {
            "code": getattr(exc, "default_code", "error"),
            "message": str(response.data.get("detail", _("The request was refused."))),
            "fields": {},
        }
    return response


class AcceptInvitationView(GenericAPIView):
    """A valid invitation token authorizes creation of its assigned new account."""

    serializer_class = AcceptInvitationSerializer
    # Public by design: possession of an unused invitation token is required.
    permission_classes = (AllowAny,)
    http_method_names = ("post", "options")

    def get_exception_handler(self) -> Any:
        """Keep the invitation contract for failures raised before post() too."""
        return invitation_exception_handler

    @extend_schema(
        operation_id="invitations_accept",
        summary="Accept an invitation and create a new account",
        description=(
            "Public token-authorized action. Creates a new account without "
            "signing in or replacing an existing browser session."
        ),
        tags=["accounts"],
        responses={
            200: InvitationAcceptedSerializer,
            400: InvitationErrorSerializer,
            403: InvitationErrorSerializer,
            405: InvitationErrorSerializer,
            503: InvitationErrorSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Validate HTTP input and leave every account decision to the service."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.accept_invitation(**serializer.validated_data)
        return Response({"accepted": True})
