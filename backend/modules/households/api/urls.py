# AI contribution: 50% or more AI-generated
"""Walk-in staff endpoints, mounted at the project /api/ prefix."""

from django.urls import path

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
]
