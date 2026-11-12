# AI contribution: 50% or more AI-generated
"""Admin review routes (US-13), mounted at /api/staff/partner-applications/."""

from django.urls import path

from modules.stores.api.staff_views import (
    StaffApplicationApproveView,
    StaffApplicationListView,
    StaffApplicationRejectView,
)

urlpatterns = [
    path("", StaffApplicationListView.as_view(), name="staff-partner-applications"),
    path(
        "<uuid:id>/approve/",
        StaffApplicationApproveView.as_view(),
        name="staff-partner-application-approve",
    ),
    path(
        "<uuid:id>/reject/",
        StaffApplicationRejectView.as_view(),
        name="staff-partner-application-reject",
    ),
]
