# AI contribution: 50% or more AI-generated
"""Walk-in staff endpoints, mounted at the project /api/ prefix."""

from django.urls import path

from modules.households.api.approval_views import WalkInApproveView
from modules.households.api.notice_views import WalkInNoticeView
from modules.households.api.views import WalkInCollectionView, WalkInDetailView

urlpatterns = [
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
]
