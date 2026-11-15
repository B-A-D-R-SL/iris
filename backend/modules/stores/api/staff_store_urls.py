# AI contribution: 50% or more AI-generated
"""Admin store routes (US-14), mounted at /api/staff/stores/."""

from django.urls import path

from modules.stores.api.staff_store_views import (
    StaffStoreDeactivateView,
    StaffStoreDetailView,
    StaffStoreListView,
    StaffStoreReactivateView,
)

urlpatterns = [
    path("", StaffStoreListView.as_view(), name="staff-stores"),
    path("<uuid:id>/", StaffStoreDetailView.as_view(), name="staff-store"),
    path(
        "<uuid:id>/deactivate/",
        StaffStoreDeactivateView.as_view(),
        name="staff-store-deactivate",
    ),
    path(
        "<uuid:id>/reactivate/",
        StaffStoreReactivateView.as_view(),
        name="staff-store-reactivate",
    ),
]
