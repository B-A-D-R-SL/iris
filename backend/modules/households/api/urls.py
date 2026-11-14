# AI contribution: 50% or more AI-generated
"""Walk-in staff endpoints, mounted at the project /api/ prefix."""

from django.urls import path

from modules.households.api.approval_views import (
    WalkInApproveView,
    WalkInDecisionSummaryView,
)
from modules.households.api.notice_views import WalkInNoticeView
from modules.households.api.views import (
    HouseholdReactivationView,
    HouseholdSuspensionView,
    WalkInCollectionView,
    WalkInDetailView,
    WalkInSubmissionView,
)

urlpatterns = [
    path(
        "staff/households/<uuid:id>/suspend/",
        HouseholdSuspensionView.as_view(),
        name="staff-households-suspend",
    ),
    path(
        "staff/households/<uuid:id>/reactivate/",
        HouseholdReactivationView.as_view(),
        name="staff-households-reactivate",
    ),
    path(
        "staff/households/<uuid:id>/submit/",
        WalkInSubmissionView.as_view(),
        name="staff-households-submit",
    ),
    path(
        "staff/households/",
        WalkInCollectionView.as_view(),
        name="staff-households-create",
    ),
    path(
        "staff/households/<uuid:id>/",
        WalkInDetailView.as_view(),
        name="staff-households-detail",
    ),
    path(
        "staff/households/<uuid:id>/notices/",
        WalkInNoticeView.as_view(),
        name="staff-households-notices",
    ),
    path(
        "staff/households/<uuid:id>/approve/",
        WalkInApproveView.as_view(),
        name="staff-households-approve",
    ),
    path(
        "staff/households/<uuid:id>/decision-summary/",
        WalkInDecisionSummaryView.as_view(),
        name="staff-households-decision-summary",
    ),
]
