# AI contribution: 50% or more AI-generated
"""Browse listings (US-36): a thin HTTP boundary over households and listings.

This view lives in reservations because it is the module allowed to read both
households (is the household approved?) and listings (what can it see?). See
[tool.importlinter] in pyproject.toml.
"""

import logging
from typing import Any

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from adapters.photo_types import PhotoStorageError
from modules.listings import queries as listing_queries
from modules.reservations.api.permissions import (
    NOT_APPROVED,
    IsBeneficiary,
    approved_household_id,
)
from modules.reservations.api.serializers import (
    BrowseErrorSerializer,
    BrowseFiltersSerializer,
    ListingCardSerializer,
    ListingPhotoUnavailable,
)

logger = logging.getLogger("iris.listings")


def _photo_urls(cards: list[dict[str, Any]]) -> dict[str, str]:
    """Only the authorized, paginated cards can receive signed links."""
    references = list(
        dict.fromkeys(card["photo_ref"] for card in cards if card["photo_ref"])
    )
    try:
        return listing_queries.photo_read_urls(references)
    except PhotoStorageError:
        logger.error(
            "listing_photo_read_failed", extra={"event": "listing_photo_read_failed"}
        )
        raise ListingPhotoUnavailable() from None


class ListingPagination(PageNumberPagination):
    """Always 20 cards a page (#506); clients choose only ?page=, not the size."""

    page_size = 20


CHECK_FIELDS = _("Check the highlighted fields.")
REFUSED = _("The request was refused.")
# Only these fixed messages are returned, never an exception's own text, which
# can repeat what the user typed.
STATUS_MESSAGES = {
    status.HTTP_401_UNAUTHORIZED: _("Sign in to see listings."),
    status.HTTP_403_FORBIDDEN: NOT_APPROVED,
    status.HTTP_404_NOT_FOUND: _("This page of listings does not exist."),
    status.HTTP_405_METHOD_NOT_ALLOWED: _("Listings can only be read here."),
    status.HTTP_503_SERVICE_UNAVAILABLE: _("Photos are temporarily unavailable."),
}
FILTER_MESSAGES = {
    "category": _("Enter a category code of 1 to 64 characters."),
    "store": _("Enter a valid store ID."),
    "today": _("Enter true or false."),
}


def browse_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Errors as { code, message, fields }, using fixed, translated messages."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data if isinstance(response.data, dict) else {}
    if isinstance(exc, ValidationError):
        names = list(data) or ["non_field_errors"]
        response.data = {
            "code": "validation_error",
            "message": str(CHECK_FIELDS),
            "fields": {
                name: [str(FILTER_MESSAGES.get(name, CHECK_FIELDS))] for name in names
            },
        }
    else:
        response.data = {
            "code": getattr(data.get("detail"), "code", None) or "request_refused",
            "message": str(STATUS_MESSAGES.get(response.status_code, REFUSED)),
            "fields": {},
        }
    return response


@extend_schema_view(
    get=extend_schema(
        operation_id="listings_list",
        summary="Browse the listings the signed-in household can see",
        tags=["listings"],
        parameters=[BrowseFiltersSerializer],
        responses={
            200: ListingCardSerializer(many=True),
            400: BrowseErrorSerializer,
            401: BrowseErrorSerializer,
            403: BrowseErrorSerializer,
            404: BrowseErrorSerializer,
            503: BrowseErrorSerializer,
        },
    )
)
class BrowseListingsView(ListAPIView):
    """The listings the signed-in household can see, 20 a page."""

    serializer_class = ListingCardSerializer
    permission_classes = (IsBeneficiary,)
    pagination_class = ListingPagination
    http_method_names = ("get", "head", "options")

    def get_exception_handler(self) -> Any:
        """Use the { code, message, fields } error shape for this view."""
        return browse_exception_handler

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """One page of the cards the signed-in household can see."""
        now = timezone.now()
        # Ownership: the household always comes from the signed-in user, never from
        # the request, so no one can browse as another household. Approval is
        # checked before the filters, so a refused household learns nothing.
        household_id = approved_household_id(request.user, at=now)
        filters = BrowseFiltersSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        cards = listing_queries.browse_listings(
            household_id,
            now,
            category=filters.validated_data.get("category"),
            store=filters.validated_data.get("store"),
            pickup_today=filters.validated_data["today"],
        )
        page = self.paginate_queryset(cards)
        context = {**self.get_serializer_context(), "photo_urls": _photo_urls(page)}
        response = self.get_paginated_response(
            self.get_serializer(page, many=True, context=context).data
        )
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response
