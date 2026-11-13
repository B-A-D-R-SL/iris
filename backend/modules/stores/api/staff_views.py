# AI contribution: 50% or more AI-generated
"""Admin review of partner applications (US-13, T-02.13.3).

The views only check access, read the request and map errors; the decision
services own the transaction, the audit event and the emails.
"""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response

from modules.stores import queries, services
from modules.stores.api.serializers import (
    PartnerApplicationErrorSerializer,
    RejectApplicationSerializer,
    StaffApplicationFilterSerializer,
    StaffPartnerApplicationSerializer,
)
from modules.stores.api.views import application_exception_handler
from modules.stores.models import PartnerApplication

ADMIN_ROLE = "admin"


class IsActiveAdmin(BasePermission):
    """Deny by default: only a signed-in, active admin passes."""

    message = _("Only admins can review partner applications.")

    def has_permission(self, request: Request, view: Any) -> bool:
        """True only for an active account with the admin role."""
        user = request.user
        return bool(
            getattr(user, "is_authenticated", False)
            and getattr(user, "is_active", False)
            and getattr(user, "role", None) == ADMIN_ROLE
        )


class ApplicationAlreadyDecidedError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "application_already_decided"
    default_detail = _("This application has already been approved or rejected.")


class ApplicationPagination(PageNumberPagination):
    """Team paging convention: ?page=1&page_size=20, at most 100."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class StaffApplicationView(GenericAPIView):
    """Shared access rule and error envelope for the review endpoints."""

    permission_classes = (IsActiveAdmin,)
    serializer_class = StaffPartnerApplicationSerializer

    def get_exception_handler(self) -> Any:
        """Use the stores error envelope: {code, message, fields}."""
        return application_exception_handler

    def get_application(self, application_id: UUID) -> PartnerApplication:
        """The application, or 404 in the team envelope."""
        application = queries.partner_application(application_id)
        if application is None:
            raise NotFound(_("This partner application does not exist."))
        return application

    def decided(self, application: PartnerApplication) -> Response:
        """200 with the application as it is after the decision."""
        return Response(self.get_serializer(application).data)


def _service_errors(exc: DjangoValidationError) -> ValidationError:
    """Keep field errors from the services (for example, the reason)."""
    if hasattr(exc, "message_dict"):
        return ValidationError(exc.message_dict)
    return ValidationError({"non_field_errors": exc.messages})


ERRORS = {
    400: PartnerApplicationErrorSerializer,
    403: PartnerApplicationErrorSerializer,
    404: PartnerApplicationErrorSerializer,
    409: PartnerApplicationErrorSerializer,
}


class StaffApplicationListView(StaffApplicationView):
    pagination_class = ApplicationPagination
    http_method_names = ("get", "head", "options")

    @extend_schema(
        operation_id="staff_partner_applications_list",
        summary="List partner applications (admin only)",
        description="Oldest first. Filter with `status`; without it, all statuses.",
        tags=["partner applications"],
        parameters=[
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                enum=["submitted", "approved", "rejected"],
                description="Only applications with this status",
            )
        ],
        responses={200: StaffPartnerApplicationSerializer(many=True), **ERRORS},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """One page of applications, oldest first."""
        filters = StaffApplicationFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        applications = queries.partner_applications(
            filters.validated_data.get("status")
        )
        page = self.paginate_queryset(applications)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


class StaffApplicationApproveView(StaffApplicationView):
    http_method_names = ("post", "options")

    @extend_schema(
        operation_id="staff_partner_applications_approve",
        summary="Approve a partner application (admin only)",
        description=(
            "Creates the store and a store-manager invitation in one transaction, "
            "records the decision in the audit log, then emails the invitation."
        ),
        tags=["partner applications"],
        request=None,
        responses={200: StaffPartnerApplicationSerializer, **ERRORS},
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        """Approve a submitted application."""
        application = self.get_application(id)
        try:
            application = services.approve_application(application, request.user)
        except services.ApplicationAlreadyDecided as exc:
            raise ApplicationAlreadyDecidedError() from exc
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        return self.decided(application)


class StaffApplicationRejectView(StaffApplicationView):
    http_method_names = ("post", "options")

    @extend_schema(
        operation_id="staff_partner_applications_reject",
        summary="Reject a partner application (admin only)",
        description=(
            "Requires a reason of at most 500 characters. Records the decision in "
            "the audit log, then emails the reason to the applicant."
        ),
        tags=["partner applications"],
        request=RejectApplicationSerializer,
        responses={200: StaffPartnerApplicationSerializer, **ERRORS},
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        """Reject a submitted application with a reason."""
        body = RejectApplicationSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        application = self.get_application(id)
        try:
            application = services.reject_application(
                application, request.user, body.validated_data["reason"]
            )
        except services.ApplicationAlreadyDecided as exc:
            raise ApplicationAlreadyDecidedError() from exc
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        return self.decided(application)
