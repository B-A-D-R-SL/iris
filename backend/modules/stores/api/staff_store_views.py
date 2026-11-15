# AI contribution: 50% or more AI-generated
"""Admin store management (US-14, T-02.14.2), mounted at /api/staff/stores/.

The views check access, read the request and map errors; the stores services
own the transaction, the cancellations, the emails and the audit events.
"""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from modules.stores import queries, services
from modules.stores.api.serializers import PartnerApplicationErrorSerializer
from modules.stores.api.staff_store_serializers import (
    StaffStoreFilterSerializer,
    StaffStoreListItemSerializer,
    StaffStorePageSerializer,
    StaffStoreSerializer,
    StaffStoreUpdateSerializer,
    StoreDeactivatedSerializer,
    StoreStatusChangeSerializer,
)
from modules.stores.api.staff_views import ApplicationPagination, IsActiveAdmin
from modules.stores.api.views import application_exception_handler
from modules.stores.models import Store

TAGS = ["stores"]
ERRORS = {
    400: PartnerApplicationErrorSerializer,
    403: PartnerApplicationErrorSerializer,
    404: PartnerApplicationErrorSerializer,
    409: PartnerApplicationErrorSerializer,
}


class IsStoreAdmin(IsActiveAdmin):
    message = _("Only admins can manage stores.")


class StoreIsBadrError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "store_is_badr"
    default_detail = _("The B.A.D.R. store cannot be deactivated.")


class StoreAlreadyInactiveError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "store_already_inactive"
    default_detail = _("This store is already deactivated.")


class StoreAlreadyActiveError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "store_already_active"
    default_detail = _("This store is already active.")


def _service_errors(exc: DjangoValidationError) -> ValidationError:
    if hasattr(exc, "message_dict"):
        return ValidationError(exc.message_dict)
    return ValidationError({"non_field_errors": exc.messages})


def _status_error(exc: services.StoreStatusUnchanged) -> APIException:
    return StoreAlreadyActiveError() if exc.is_active else StoreAlreadyInactiveError()


class StaffStoreView(GenericAPIView):
    """Shared access rule and error envelope for the store endpoints."""

    permission_classes = (IsStoreAdmin,)
    serializer_class = StaffStoreSerializer

    def get_exception_handler(self) -> Any:
        """Use the stores error envelope: {code, message, fields}."""
        return application_exception_handler

    def get_store(self, store_id: UUID) -> Store:
        store = queries.staff_store(store_id)
        if store is None:
            raise NotFound(_("This store does not exist."))
        return store

    def detail(
        self, store: Store, serializer_class: Any = None, **extra: Any
    ) -> Response:
        """The store with what deactivating it now would cancel."""
        preview = queries.deactivation_preview(store.pk, timezone.now())
        serializer = (serializer_class or StaffStoreSerializer)(
            store, context={"request": self.request, "preview": preview}
        )
        return Response({**serializer.data, **extra})


class StaffStoreListView(StaffStoreView):
    pagination_class = ApplicationPagination
    http_method_names = ("get", "head", "options")

    @extend_schema(
        operation_id="staff_stores_list",
        summary="List stores (admin only)",
        description=(
            "By name. `q` searches the name and address; `status` keeps active or "
            "deactivated stores. `counts` gives the totals for the same search."
        ),
        tags=TAGS,
        parameters=[
            OpenApiParameter("q", OpenApiTypes.STR, description="Name or address"),
            OpenApiParameter("status", OpenApiTypes.STR, enum=["active", "inactive"]),
        ],
        responses={200: StaffStorePageSerializer, **ERRORS},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        filters = StaffStoreFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        q = filters.validated_data.get("q")
        page = self.paginate_queryset(
            queries.staff_stores(q, filters.validated_data.get("status"))
        )
        counts = queries.open_listing_counts(
            [store.pk for store in page], timezone.now()
        )
        rows = StaffStoreListItemSerializer(
            page, many=True, context={"open_listings": counts}
        )
        response = self.get_paginated_response(rows.data)
        response.data["counts"] = queries.status_counts(q)
        return response


class StaffStoreDetailView(StaffStoreView):
    http_method_names = ("get", "patch", "head", "options")

    @extend_schema(
        operation_id="staff_stores_retrieve",
        summary="Get a store (admin only)",
        description="Includes what deactivating it now would cancel.",
        tags=TAGS,
        responses={200: StaffStoreSerializer, **ERRORS},
    )
    def get(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        return self.detail(self.get_store(id))

    @extend_schema(
        operation_id="staff_stores_partial_update",
        summary="Edit a store (admin only)",
        description=(
            "Send only the fields to change. The id, B.A.D.R. flag, application, "
            "status and timestamps cannot be changed here. Records the changed "
            "field names in the audit log."
        ),
        tags=TAGS,
        request=StaffStoreUpdateSerializer,
        responses={200: StaffStoreSerializer, **ERRORS},
    )
    def patch(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        body = StaffStoreUpdateSerializer(data=request.data, partial=True)
        body.is_valid(raise_exception=True)
        self.get_store(id)
        try:
            store = services.update_store(id, body.validated_data, request.user)
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        return self.detail(store)


class StaffStoreDeactivateView(StaffStoreView):
    http_method_names = ("post", "options")

    @extend_schema(
        operation_id="staff_stores_deactivate",
        summary="Deactivate a store (admin only)",
        description=(
            "Requires a reason. The store can no longer post; its listings whose "
            "pickup has not ended are cancelled, their reservations become "
            "`cancelled_by_store` with no strike, and each household is emailed. "
            "The B.A.D.R. store cannot be deactivated."
        ),
        tags=TAGS,
        request=StoreStatusChangeSerializer,
        responses={200: StoreDeactivatedSerializer, **ERRORS},
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        body = StoreStatusChangeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        self.get_store(id)
        try:
            result = services.deactivate_store(
                id, request.user, body.validated_data["reason"]
            )
        except services.StoreIsBadr as exc:
            raise StoreIsBadrError() from exc
        except services.StoreStatusUnchanged as exc:
            raise _status_error(exc) from exc
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        return self.detail(
            result.store,
            StoreDeactivatedSerializer,
            listings_cancelled=result.listings_cancelled,
            reservations_cancelled=result.reservations_cancelled,
        )


class StaffStoreReactivateView(StaffStoreView):
    http_method_names = ("post", "options")

    @extend_schema(
        operation_id="staff_stores_reactivate",
        summary="Reactivate a store (admin only)",
        description=(
            "Requires a reason. The store can post again; cancelled listings stay "
            "cancelled."
        ),
        tags=TAGS,
        request=StoreStatusChangeSerializer,
        responses={200: StaffStoreSerializer, **ERRORS},
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        body = StoreStatusChangeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        self.get_store(id)
        try:
            store = services.reactivate_store(
                id, request.user, body.validated_data["reason"]
            )
        except services.StoreStatusUnchanged as exc:
            raise _status_error(exc) from exc
        except DjangoValidationError as exc:
            raise _service_errors(exc) from exc
        return self.detail(store)
