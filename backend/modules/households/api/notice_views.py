# AI contribution: 50% or more AI-generated
"""Staff-only endpoint recording an adult's notice of assessment on a walk-in draft."""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from modules.documents.services import NoticeServiceUnavailable
from modules.households import services
from modules.households.api.notice_serializers import (
    WalkInNoticeInputSerializer,
    WalkInNoticeReadSerializer,
)
from modules.households.api.views import (
    IsIntakeWorkerOrAdmin,
    WalkInErrorHandlingMixin,
    _service_validation,
)
from modules.households.models import Household


class WalkInNoticeView(WalkInErrorHandlingMixin, GenericAPIView):
    serializer_class = WalkInNoticeInputSerializer
    permission_classes = (IsIntakeWorkerOrAdmin,)
    parser_classes = (MultiPartParser, FormParser)

    @extend_schema(
        request={"multipart/form-data": WalkInNoticeInputSerializer},
        responses={201: WalkInNoticeReadSerializer},
        tags=["staff households"],
        summary="Record an adult's notice of assessment or non-filing reason",
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        serializer = WalkInNoticeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            notice = services.record_walk_in_notice(
                id, serializer.validated_data, request.user
            )
        except Household.DoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        except NoticeServiceUnavailable as exc:
            body = {"code": exc.code, "message": str(exc.message), "fields": {}}
            return Response(body, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(
            WalkInNoticeReadSerializer(notice).data, status=status.HTTP_201_CREATED
        )
