# AI contribution: 50% or more AI-generated
"""Pickup history (US-48): GET /api/reservations/me/.

Thin: check the role, validate the filter, find the household the signed-in
user holds and page ``queries.household_history``. The household always comes
from the signed-in user, never from the request, so no one can read another
household's reservations. Its status does not matter (BR-RES-011).
"""

from datetime import UTC, datetime
from typing import Any, cast

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param
from rest_framework.views import exception_handler

from modules.households import queries as household_queries
from modules.reservations import queries
from modules.reservations.api.history_serializers import (
    HistoryEntrySerializer,
    HistoryFiltersSerializer,
)
from modules.reservations.api.permissions import IsBeneficiary
from modules.reservations.api.serializers import BrowseErrorSerializer

CHECK_FIELDS = _("Check the highlighted fields.")
# Only these fixed messages are returned, never an exception's own text, which
# can repeat what the user typed.
STATUS_MESSAGES = {
    status.HTTP_401_UNAUTHORIZED: _("Sign in to see your reservations."),
    status.HTTP_403_FORBIDDEN: _("Only household accounts have reservations."),
    status.HTTP_404_NOT_FOUND: _("This page of reservations does not exist."),
    status.HTTP_405_METHOD_NOT_ALLOWED: _("Reservations can only be read here."),
}
FILTER_MESSAGES = {
    "status": _(
        "Enter one of reserved, picked_up, cancelled, cancelled_by_store or no_show."
    ),
    "as_of": _("Enter a date and time, as in the next page link."),
}


def history_exception_handler(
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
            "message": str(
                STATUS_MESSAGES.get(response.status_code, _("The request was refused."))
            ),
            "fields": {},
        }
    return response


class HistoryPagination(PageNumberPagination):
    """Always 20 reservations a page; clients choose only ?page=, not the size.

    The next link carries ``as_of``, the time page 1 was read, so every later
    page is ordered as at that time.
    """

    page_size = 20
    as_of: datetime | None = None

    def get_next_link(self) -> str | None:
        """The next page's link, with ``as_of`` added."""
        link = super().get_next_link()
        if link is None or self.as_of is None:
            return link
        moment = self.as_of.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return replace_query_param(link, "as_of", moment)


@extend_schema_view(
    get=extend_schema(
        operation_id="reservations_me_list",
        summary="The signed-in household's reservations and pickup history",
        tags=["reservations"],
        parameters=[HistoryFiltersSerializer],
        responses={
            200: HistoryEntrySerializer(many=True),
            400: BrowseErrorSerializer,
            401: BrowseErrorSerializer,
            403: BrowseErrorSerializer,
            404: BrowseErrorSerializer,
        },
    )
)
class HouseholdHistoryView(ListAPIView):
    """Upcoming reservations first, then the past ones, 20 a page."""

    serializer_class = HistoryEntrySerializer
    permission_classes = (IsBeneficiary,)
    pagination_class = HistoryPagination
    http_method_names = ("get", "head", "options")

    def get_exception_handler(self) -> Any:
        """Use the { code, message, fields } error shape for this view."""
        return history_exception_handler

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """One page of the signed-in household's reservations."""
        now = timezone.now()
        filters = HistoryFiltersSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        # Later pages are ordered as at page 1's time, so a pickup window that
        # ends in between cannot repeat or skip a row. Codes follow ``now``.
        as_of = min(filters.validated_data.get("as_of", now), now)
        cast(HistoryPagination, self.paginator).as_of = as_of
        # Any file status: a suspended or expired household still sees what it
        # received. No household, or an anonymized one, gives an empty list.
        household_id = household_queries.held_household_id(request.user.pk)
        rows = queries.household_history(
            household_id,
            now=now,
            as_of=as_of,
            status=filters.validated_data.get("status"),
        )
        page = self.paginate_queryset(rows)
        response = self.get_paginated_response(
            self.get_serializer(queries.history_entries(page), many=True).data
        )
        # The page holds pickup codes: never cache it or leak it in a referrer.
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response
