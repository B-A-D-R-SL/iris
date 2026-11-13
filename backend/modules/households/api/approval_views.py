# AI contribution: 50% or more AI-generated
"""Staff endpoint that asks for the walk-in decision (US-18).

The view only checks access and maps errors; approve_walk_in (#469) checks the
file, runs eligibility, saves the outcome, writes the audit event and queues
the set-password email in one transaction.
"""

from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from modules.households import queries, services
from modules.households.api.views import (
    IsIntakeWorkerOrAdmin,
    WalkInErrorHandlingMixin,
    _service_validation,
)


class WalkInDecisionSerializer(serializers.Serializer):
    """The outcome staff explain to the household at the counter."""

    id = serializers.UUIDField(read_only=True)
    # approved, rejected or review_required (Household.Status).
    status = serializers.CharField(read_only=True)
    # Codes such as INCOME_ABOVE_LICO or NAME_MISMATCH, comma-separated.
    status_reason = serializers.CharField(read_only=True)
    approved_at = serializers.DateTimeField(read_only=True, allow_null=True)
    expires_at = serializers.DateTimeField(read_only=True, allow_null=True)


class WalkInApproveView(WalkInErrorHandlingMixin, GenericAPIView):
    serializer_class = WalkInDecisionSerializer
    permission_classes = (IsIntakeWorkerOrAdmin,)

    @extend_schema(
        request=None,
        responses={200: WalkInDecisionSerializer},
        tags=["staff households"],
        summary="Decide a walk-in file: approved, rejected or sent to review",
        description=(
            "Runs eligibility on the recorded notices. Answers 200 with the outcome; "
            "400 when the file is incomplete or cannot be decided in its status."
        ),
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        """Ask for the decision on one walk-in file."""
        household = queries.walk_in_for_staff(id, request.user)
        if household is None:
            raise Http404
        try:
            household = services.approve_walk_in(household, request.user)
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(WalkInDecisionSerializer(household).data)
