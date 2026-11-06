# AI contribution: 50% or more AI-generated
"""The API error envelope `{code, message, fields}` for documents endpoints."""

from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler


class StorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "storage_unavailable"
    default_detail = _("Notice storage is unavailable. Try again later.")


def documents_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """DRF's handler, reshaped; no internal detail reaches the client."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data.get("detail") if isinstance(response.data, dict) else None
    response.data = {
        "code": getattr(exc, "default_code", "request_refused"),
        "message": str(detail or _("The request was refused.")),
        "fields": {},
    }
    return response
