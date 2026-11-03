"""Admin-only audit event search."""

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission

from modules.audit.api.serializers import AuditEventSerializer, AuditSearchSerializer
from modules.audit.queries import search_events


class IsAuditAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user.is_authenticated and user.is_active and user.role == "admin")


class AuditPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(
    tags=["audit"],
    summary="Search audit events (admin only)",
    parameters=[
        OpenApiParameter("household", OpenApiTypes.UUID, description="Household ID"),
        OpenApiParameter("actor", OpenApiTypes.UUID, description="Staff user ID"),
        OpenApiParameter(
            "from", OpenApiTypes.DATE, description="First Montreal date, inclusive"
        ),
        OpenApiParameter(
            "to", OpenApiTypes.DATE, description="Last Montreal date, inclusive"
        ),
    ],
)
class AuditSearchView(generics.ListAPIView):
    serializer_class = AuditEventSerializer
    permission_classes = (IsAuditAdmin,)
    pagination_class = AuditPagination
    http_method_names = ("get", "head", "options")

    def get_queryset(self):
        params = self.request.query_params
        data = {
            internal: params[external]
            for external, internal in (
                ("household", "household"),
                ("actor", "actor"),
                ("from", "date_from"),
                ("to", "date_to"),
            )
            if params.get(external)
        }
        serializer = AuditSearchSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return search_events(**serializer.validated_data)
