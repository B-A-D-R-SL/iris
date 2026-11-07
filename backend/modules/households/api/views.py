# AI contribution: 50% or more AI-generated
"""Session-authenticated, staff-only walk-in registration endpoints."""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from modules.audit import services as audit_services
from modules.households import queries, services
from modules.households.api.search_serializers import (
    HouseholdSearchInputSerializer,
    HouseholdSearchResultSerializer,
)
from modules.households.api.serializers import (
    WalkInDraftInputSerializer,
    WalkInDraftReadSerializer,
)
from modules.households.models import Household


def _flatten_errors(detail: Any, prefix: str = "") -> dict[str, list[str]]:
    if isinstance(detail, dict):
        fields: dict[str, list[str]] = {}
        for key, value in detail.items():
            label = f"{prefix}.{key}" if prefix else str(key)
            fields.update(_flatten_errors(value, label))
        return fields
    if isinstance(detail, list) and any(isinstance(v, (dict, list)) for v in detail):
        fields = {}
        for index, item in enumerate(detail):
            fields.update(_flatten_errors(item, f"{prefix}[{index}]"))
        return fields
    if not isinstance(detail, list):
        detail = [detail]
    return {prefix or "non_field_errors": [str(value) for value in detail]}


def walk_in_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        response.data = {
            "code": "validation_error",
            "message": str(_("Check the highlighted fields.")),
            "fields": _flatten_errors(response.data),
        }
    else:
        message = response.data.get("detail", _("The request was refused."))
        response.data = {
            "code": getattr(exc, "default_code", "request_refused"),
            "message": str(message),
            "fields": {},
        }
    return response


class WalkInErrorHandlingMixin:
    def get_exception_handler(self) -> Any:
        return walk_in_exception_handler


class IsIntakeWorkerOrAdmin(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and getattr(user, "role", None) in services.STAFF_ROLES
        )


def _validated(data: Any, *, partial: bool = False) -> dict[str, Any]:
    serializer = WalkInDraftInputSerializer(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return dict(serializer.validated_data)


def _service_validation(exc: DjangoValidationError) -> ValidationError:
    if hasattr(exc, "message_dict"):
        return ValidationError(exc.message_dict)
    return ValidationError({"non_field_errors": exc.messages})


class HouseholdSearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class WalkInCollectionView(WalkInErrorHandlingMixin, GenericAPIView):
    serializer_class = WalkInDraftInputSerializer
    permission_classes = (IsIntakeWorkerOrAdmin,)
    pagination_class = HouseholdSearchPagination

    @extend_schema(
        operation_id="staff_households_list",
        parameters=[
            OpenApiParameter(
                "q",
                str,
                description="Partial name, email, phone, member number or address. Blank returns no files.",
            ),
        ],
        responses={200: HouseholdSearchResultSerializer(many=True)},
        tags=["staff households"],
        summary="Find a household (intake workers and administrators)",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        params = HouseholdSearchInputSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        page = self.paginate_queryset(queries.search(params.validated_data["q"]))
        # Record only returned IDs, never the search text or personal details.
        # A failed audit prevents disclosure. Search queries themselves only read.
        with transaction.atomic():
            data = HouseholdSearchResultSerializer(page, many=True).data
            if request.method == "GET":
                audit_services.record_household_views(
                    request.user, (household.pk for household in page)
                )
        response = self.get_paginated_response(data)
        response["Cache-Control"] = "private, no-store"
        return response

    @extend_schema(
        request=WalkInDraftInputSerializer,
        responses={201: WalkInDraftReadSerializer},
        tags=["staff households"],
        summary="Create a resumable walk-in household draft",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        data = _validated(request.data)
        try:
            household = services.create_walk_in(data, request.user)
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(
            WalkInDraftReadSerializer(household).data, status=status.HTTP_201_CREATED
        )


class WalkInDetailView(WalkInErrorHandlingMixin, GenericAPIView):
    serializer_class = WalkInDraftInputSerializer
    permission_classes = (IsIntakeWorkerOrAdmin,)

    @staticmethod
    def _get_household(id: UUID) -> Household:
        household = queries.walk_in_for_staff(id)
        if household is None:
            raise Http404
        return household

    @extend_schema(
        responses={200: WalkInDraftReadSerializer},
        tags=["staff households"],
        summary="Resume an existing walk-in household draft",
    )
    def get(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        return Response(WalkInDraftReadSerializer(self._get_household(id)).data)

    @extend_schema(
        request=WalkInDraftInputSerializer,
        responses={200: WalkInDraftReadSerializer},
        tags=["staff households"],
        summary="Edit an existing walk-in household draft",
    )
    def patch(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        data = _validated(request.data, partial=True)
        try:
            household = services.update_draft(id, data, request.user)
        except Household.DoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(WalkInDraftReadSerializer(household).data)
