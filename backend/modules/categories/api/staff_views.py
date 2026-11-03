# AI contribution: 50% or more AI-generated
"""Admin endpoints for managing categories (US-35, T-05.35.2).

Thin views: check the admin role, validate, call a service. There is no delete:
a category in use keeps its code and is deactivated instead.
"""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from modules.categories import queries, services
from modules.categories.api.serializers import (
    CategoryErrorSerializer,
    StaffCategorySerializer,
)
from modules.categories.models import Category


class CategoryRulesNotSeeded(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "rules_unavailable"
    default_detail = _("Listing rules must be seeded before categories can be saved.")


class IsActiveAdmin(BasePermission):
    message = _("Only admins can manage categories.")

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return bool(
            user.is_authenticated
            and user.is_active
            and getattr(user, "role", None) == "admin"
        )


def category_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """Team error envelope: { "code", "message", "fields" }."""
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
            "code": getattr(exc, "default_code", "request_refused"),
            "message": str(response.data.get("detail", _("The request was refused."))),
            "fields": {},
        }
    return response


def _save(action: Any) -> Category:
    """Run a service and turn its errors into API errors."""
    try:
        return action()
    except Category.DoesNotExist as exc:
        raise Http404 from exc
    except services.CategoryRulesUnavailable as exc:
        raise CategoryRulesNotSeeded from exc
    except DjangoValidationError as exc:
        raise ValidationError(
            exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        ) from exc


class StaffCategoryMixin:
    permission_classes = (IsActiveAdmin,)
    serializer_class = StaffCategorySerializer

    def get_exception_handler(self) -> Any:
        return category_exception_handler


ERRORS = {
    400: CategoryErrorSerializer,
    403: CategoryErrorSerializer,
    503: CategoryErrorSerializer,
}


class StaffCategoryListView(StaffCategoryMixin, GenericAPIView):
    @extend_schema(
        operation_id="staff_categories_list",
        tags=["staff categories"],
        summary="List every category, active or not (admin)",
        responses={
            200: StaffCategorySerializer(many=True),
            403: CategoryErrorSerializer,
        },
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        categories = queries.list_all_categories()
        return Response(StaffCategorySerializer(categories, many=True).data)

    @extend_schema(
        operation_id="staff_categories_create",
        tags=["staff categories"],
        summary="Add a category (admin)",
        request=StaffCategorySerializer,
        responses={201: StaffCategorySerializer, **ERRORS},
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = StaffCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = _save(
            lambda: services.create_category(serializer.validated_data, request.user)
        )
        return Response(
            StaffCategorySerializer(category).data, status=status.HTTP_201_CREATED
        )


class StaffCategoryDetailView(StaffCategoryMixin, GenericAPIView):
    @extend_schema(
        operation_id="staff_categories_update",
        tags=["staff categories"],
        summary="Rename, change, deactivate or reactivate a category (admin)",
        request=StaffCategorySerializer(partial=True),
        responses={
            200: StaffCategorySerializer,
            404: CategoryErrorSerializer,
            **ERRORS,
        },
    )
    def patch(self, request: Request, code: str, *args: Any, **kwargs: Any) -> Response:
        category = queries.get_category(code)
        if category is None:
            raise Http404
        serializer = StaffCategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = _save(
            lambda: services.update_category(
                code, serializer.validated_data, request.user
            )
        )
        return Response(StaffCategorySerializer(updated).data)
