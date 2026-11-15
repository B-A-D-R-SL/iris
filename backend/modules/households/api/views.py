# AI contribution: 50% or more AI-generated
"""Session-authenticated, staff-only walk-in registration endpoints."""

from typing import Any
from uuid import UUID

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from modules.audit import services as audit_services
from modules.households import queries, services
from modules.households.api.pagination import HouseholdSearchPagination
from modules.households.api.search_serializers import (
    HouseholdSearchInputSerializer,
    HouseholdSearchResultSerializer,
)
from modules.households.api.serializers import (
    HouseholdErrorSerializer,
    HouseholdStatusInputSerializer,
    HouseholdStatusReadSerializer,
    WalkInDraftInputSerializer,
    WalkInDraftReadSerializer,
    WalkInSubmissionInputSerializer,
    WalkInSubmissionReadSerializer,
)
from modules.households.exceptions import HouseholdUnavailable
from modules.households.models import Household
from modules.households.policies import can_manage_walk_ins, can_suspend_households


def _flatten_errors(detail: Any, prefix: str = "") -> dict[str, list[str]]:
    """Turn nested serializer errors into field paths used by the staff forms."""
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
    """Return the shared validation envelope while retaining refusal status codes."""
    if isinstance(exc, HouseholdUnavailable):
        return Response(
            {
                "code": "household_unavailable",
                "message": str(
                    _(
                        "Household registration is temporarily unavailable. Please try again."
                    )
                ),
                "fields": {},
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
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
        """Apply the walk-in error contract to every staff household operation."""
        return walk_in_exception_handler


class IsIntakeWorkerOrAdmin(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        """Check the same staff permission used by edits and advertised actions."""
        return can_manage_walk_ins(request.user)


class IsAdmin(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        """Allow only active administrators to change household status."""
        return can_suspend_households(request.user)


def _validated(data: Any, *, partial: bool = False) -> dict[str, Any]:
    """Validate submitted draft fields before passing them to a service."""
    serializer = WalkInDraftInputSerializer(data=data, partial=partial)
    serializer.is_valid(raise_exception=True)
    return dict(serializer.validated_data)


def _service_validation(exc: DjangoValidationError) -> ValidationError:
    """Preserve field errors when adapting service validation to the API contract."""
    if hasattr(exc, "message_dict"):
        return ValidationError(exc.message_dict)
    return ValidationError({"non_field_errors": exc.messages})


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
        """Record disclosure audits before returning authorized search results."""
        params = HouseholdSearchInputSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        page = self.paginate_queryset(
            queries.search_for_staff(params.validated_data["q"], request.user)
        )
        # Record only returned IDs, never the search text or personal details.
        # A failed audit prevents disclosure. Search queries themselves only read.
        with transaction.atomic():
            data = HouseholdSearchResultSerializer(
                page, many=True, context=self.get_serializer_context()
            ).data
            if request.method == "GET":
                audit_services.record_household_views(
                    request.user, (household.pk for household in page)
                )
        response = self.get_paginated_response(data)
        response["Cache-Control"] = "private, no-store"
        return response

    @extend_schema(
        request=WalkInDraftInputSerializer,
        responses={201: WalkInDraftReadSerializer, 503: HouseholdErrorSerializer},
        tags=["staff households"],
        summary="Create a resumable walk-in household draft",
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create a resumable draft and return validated field errors on refusal."""
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
    def _get_household(id: UUID, staff_user: AbstractBaseUser) -> Household:
        household = queries.walk_in_for_staff(id, staff_user)
        if household is None:
            raise Http404
        return household

    @extend_schema(
        responses={200: WalkInDraftReadSerializer},
        tags=["staff households"],
        summary="View a household file (staff)",
    )
    def get(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        with transaction.atomic():
            household = queries.household_for_staff(id, request.user)
            if household is None:
                raise Http404
            data = self.get_read_serializer(household).data
            if request.method == "GET":
                audit_services.record(
                    request.user, "view", "household", household.pk, {}
                )
        response = Response(data)
        response["Cache-Control"] = "private, no-store"
        return response

    def get_read_serializer(self, household: Household) -> WalkInDraftReadSerializer:
        return WalkInDraftReadSerializer(
            household, context=self.get_serializer_context()
        )

    @extend_schema(
        request=WalkInDraftInputSerializer,
        responses={200: WalkInDraftReadSerializer, 503: HouseholdErrorSerializer},
        tags=["staff households"],
        summary="Edit an existing walk-in household draft",
    )
    def patch(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        self._get_household(id, request.user)
        data = _validated(request.data, partial=True)
        try:
            household = services.update_draft(id, data, request.user)
        except Household.DoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(WalkInDraftReadSerializer(household).data)


class WalkInSubmissionView(WalkInErrorHandlingMixin, GenericAPIView):
    serializer_class = WalkInSubmissionInputSerializer
    permission_classes = (IsIntakeWorkerOrAdmin,)

    @extend_schema(
        request=WalkInSubmissionInputSerializer,
        responses={200: WalkInSubmissionReadSerializer, 503: HouseholdErrorSerializer},
        tags=["staff households"],
        summary="Submit a walk-in draft and check for duplicates",
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        if queries.walk_in_for_staff(id, request.user) is None:
            raise Http404
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            household = services.submit_walk_in(id, request.user)
        except Household.DoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(WalkInSubmissionReadSerializer(household).data)


class HouseholdStatusView(WalkInErrorHandlingMixin, GenericAPIView):
    serializer_class = HouseholdStatusInputSerializer
    permission_classes = (IsAdmin,)
    reactivate = False

    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            household = services.change_suspension(
                id,
                serializer.validated_data["reason"],
                request.user,
                reactivate=self.reactivate,
            )
        except Household.DoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(HouseholdStatusReadSerializer(household).data)


class HouseholdSuspensionView(HouseholdStatusView):
    @extend_schema(
        request=HouseholdStatusInputSerializer,
        responses={
            200: HouseholdStatusReadSerializer,
            400: HouseholdErrorSerializer,
            403: HouseholdErrorSerializer,
            404: HouseholdErrorSerializer,
        },
        tags=["staff households"],
        summary="Suspend a household file (administrator)",
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, id, *args, **kwargs)


class HouseholdReactivationView(HouseholdStatusView):
    reactivate = True

    @extend_schema(
        request=HouseholdStatusInputSerializer,
        responses={
            200: HouseholdStatusReadSerializer,
            400: HouseholdErrorSerializer,
            403: HouseholdErrorSerializer,
            404: HouseholdErrorSerializer,
        },
        tags=["staff households"],
        summary="Reactivate a household file (administrator)",
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, id, *args, **kwargs)
