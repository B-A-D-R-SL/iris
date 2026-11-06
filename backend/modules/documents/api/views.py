# AI contribution: 50% or more AI-generated
"""Staff-only endpoints for notice files: a signed link, then the download (BR-DOC-006)."""

from typing import Any
from uuid import UUID

from django.http import HttpResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response

from modules.accounts.queries import is_intake_staff
from modules.documents import services
from modules.documents.api.errors import NoticeUnavailable, documents_exception_handler
from modules.documents.api.serializers import NoticeFileLinkSerializer
from modules.documents.domain.notice import NOTICE_CONTENT_TYPES


class IsIntakeWorkerOrAdmin(BasePermission):
    """Deny by default: only active intake workers and admins (review rule 4)."""

    def has_permission(self, request: Request, view: Any) -> bool:
        return is_intake_staff(request.user)


class _NoticeFileView(GenericAPIView):
    permission_classes = (IsIntakeWorkerOrAdmin,)

    def get_exception_handler(self) -> Any:
        return documents_exception_handler


class NoticeFileLinkView(_NoticeFileView):
    serializer_class = NoticeFileLinkSerializer

    @extend_schema(
        responses={200: NoticeFileLinkSerializer},
        tags=["staff notices"],
        summary="Get a short-lived link to a notice of assessment file",
    )
    def get(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        try:
            link = services.issue_file_link(id, request.user)
        except services.NoticeFileNotFound as exc:
            raise NotFound(_("This notice has no file.")) from exc
        except services.NoticeServiceUnavailable as exc:
            raise NoticeUnavailable(exc) from exc
        url = reverse("staff-notice-file-download", kwargs={"token": link.token})
        data = {"url": url, "expires_at": link.expires_at}
        return Response(NoticeFileLinkSerializer(data).data)


class NoticeFileDownloadView(_NoticeFileView):
    def perform_content_negotiation(
        self, request: Request, force: bool = False
    ) -> tuple[Any, str]:
        """The file sets its own type, whatever the client accepts; errors are JSON."""
        return super().perform_content_negotiation(request, force=True)

    @extend_schema(
        responses={
            (200, content_type): OpenApiTypes.BINARY
            for content_type in NOTICE_CONTENT_TYPES
        },
        tags=["staff notices"],
        summary="Download a notice of assessment file through a signed link",
    )
    def get(
        self, request: Request, token: str, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        try:
            notice_file = services.open_file(token, request.user)
        except services.NoticeFileNotFound as exc:
            raise NotFound(_("This file link is invalid or has expired.")) from exc
        except services.NoticeServiceUnavailable as exc:
            raise NoticeUnavailable(exc) from exc
        response = HttpResponse(
            notice_file.content, content_type=notice_file.content_type
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{notice_file.filename}"'
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
