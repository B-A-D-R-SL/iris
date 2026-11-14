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

from modules.households import approval_services, queries
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
    # True when the email already has an account: approved, but no invitation sent.
    invitation_not_sent = serializers.BooleanField(read_only=True)


class WalkInDecisionSummarySerializer(serializers.Serializer):
    """Numbers and next step the API works out before the decision."""

    household_size = serializers.IntegerField(read_only=True)
    adult_count = serializers.IntegerField(read_only=True)
    # Null until every adult has a notice the rules can add up.
    total_income_cents = serializers.IntegerField(read_only=True, allow_null=True)
    threshold_cents = serializers.IntegerField(read_only=True, allow_null=True)
    ready_for_decision = serializers.BooleanField(read_only=True)
    will_go_to_review = serializers.BooleanField(read_only=True)
    # Income within the threshold; null when the file goes to review or is not ready.
    eligible = serializers.BooleanField(read_only=True, allow_null=True)
    # Set only when approving would approve the file: from file_validity.
    approved_months = serializers.IntegerField(read_only=True, allow_null=True)
    valid_until = serializers.DateTimeField(read_only=True, allow_null=True)


class WalkInDecisionSummaryView(WalkInErrorHandlingMixin, GenericAPIView):
    serializer_class = WalkInDecisionSummarySerializer
    permission_classes = (IsIntakeWorkerOrAdmin,)

    @extend_schema(
        responses={200: WalkInDecisionSummarySerializer},
        tags=["staff households"],
        summary="What the decision would use and whether it goes to review",
        description="Read-only. Household size, total income and the LICO threshold.",
    )
    def get(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        """Summarize one walk-in file before the decision."""
        household = queries.walk_in_for_staff(id, request.user)
        if household is None:
            raise Http404
        try:
            summary = approval_services.decision_summary(household, request.user)
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(WalkInDecisionSummarySerializer(summary).data)


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
            household = approval_services.approve_walk_in(household, request.user)
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(WalkInDecisionSerializer(household).data)
