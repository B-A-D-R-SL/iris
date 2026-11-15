# AI contribution: 50% or more AI-generated
"""Public, rate-limited partner application endpoint (US-12)."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView, exception_handler

from modules.stores import services
from modules.stores.api.serializers import (
    PartnerApplicationErrorSerializer,
    PartnerApplicationSerializer,
    SubmittedPartnerApplicationSerializer,
)


def _without_port(address: str) -> str:
    """Drop a port from "1.2.3.4:5678" or "[2001:db8::1]:5678"; keep bare IPv6."""
    if address.startswith("[") and "]" in address:
        return address[1 : address.index("]")]
    if address.count(":") == 1:
        return address.split(":", 1)[0]
    return address


class PartnerApplicationThrottle(SimpleRateThrottle):
    """5 requests per hour per client IP, whether or not the caller is signed in.

    DRF's ScopedRateThrottle counts signed-in users by account, which would give
    each account its own allowance on a shared IP. A forwarded address may carry
    the connection's port, which changes on every connection, so it is dropped.
    """

    scope = "partner_applications"

    def get_cache_key(self, request: Request, view: APIView) -> str:
        ident = _without_port(self.get_ident(request))
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ApplicationAlreadyOpenError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "application_already_open"


def _messages(value: Any) -> list[str]:
    """Flatten DRF's nested list/dict errors into one list of strings."""
    if isinstance(value, dict):
        return [message for item in value.values() for message in _messages(item)]
    if isinstance(value, list):
        return [message for item in value for message in _messages(item)]
    return [str(value)]


def application_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Return the API convention envelope: {code, message, fields}."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        fields = response.data if isinstance(response.data, dict) else {}
        response.data = {
            "code": "validation_error",
            "message": str(_("Check the highlighted fields.")),
            "fields": {key: _messages(value) for key, value in fields.items()},
        }
    elif isinstance(exc, Throttled):
        response.data = {
            "code": "throttled",
            "message": str(
                _(
                    "Too many applications were sent from this connection. "
                    "Try again later."
                )
            ),
            "fields": {},
        }
    else:
        response.data = {
            "code": exc.get_codes() if isinstance(exc, APIException) else "error",
            "message": str(response.data.get("detail", _("The request was refused."))),
            "fields": {},
        }
    return response


class PartnerApplicationCreateView(GenericAPIView):
    serializer_class = PartnerApplicationSerializer
    # Public by design: prospective partners apply before they have an account.
    permission_classes = (AllowAny,)
    throttle_classes = (PartnerApplicationThrottle,)
    http_method_names = ("post", "options")

    def get_exception_handler(self) -> Any:
        return application_exception_handler

    @extend_schema(
        operation_id="partner_applications_create",
        summary="Apply to become a partner store",
        description=(
            "Public form, no account needed. Limited to 5 requests per hour per "
            "IP address. The contact receives a confirmation email."
        ),
        tags=["partner applications"],
        responses={
            201: SubmittedPartnerApplicationSerializer,
            400: PartnerApplicationErrorSerializer,
            409: PartnerApplicationErrorSerializer,
            429: PartnerApplicationErrorSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            application = services.submit_application(
                serializer.validated_data, language=(get_language() or "fr")[:2]
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        except services.ApplicationAlreadyOpen as exc:
            raise ApplicationAlreadyOpenError(
                _(
                    "An application is already in progress. An application made "
                    "with %(email)s is already waiting for an answer from B.A.D.R. "
                    "You have nothing else to do: we will write to you by email."
                )
                % {"email": exc.email}
            ) from exc
        return Response(
            SubmittedPartnerApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )
