# AI contribution: 50% or more AI-generated
"""Browse listings (US-36): a thin HTTP boundary over households and listings.

This view lives in reservations because it is the module allowed to read both
households (is the household approved?) and listings (what can it see?). See
[tool.importlinter] in pyproject.toml.
"""

from typing import Any

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from modules.listings import queries as listing_queries
from modules.reservations.api.permissions import IsBeneficiary, approved_household_id
from modules.reservations.api.serializers import (
    BrowseErrorSerializer,
    BrowseFiltersSerializer,
    ListingCardSerializer,
)


class ListingPagination(PageNumberPagination):
    """20 cards a page (US-36); ?page_size= goes up to 100 (API conventions)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def browse_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Errors as { code, message, fields }, in the user's language."""
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
                key: [str(message) for message in value]
                if isinstance(value, list)
                else [str(value)]
                for key, value in fields.items()
            },
        }
    else:
        detail = response.data.get("detail", _("The request was refused."))
        response.data = {
            "code": getattr(detail, "code", None) or "request_refused",
            "message": str(detail),
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
        return browse_exception_handler

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        now = timezone.now()
        # Approval first: a refused household learns nothing from its filters.
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
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
