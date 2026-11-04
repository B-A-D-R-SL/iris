# AI contribution: 50% or more AI-generated
"""Admin routes for categories (US-35), mounted at /api/staff/categories/."""

from django.urls import path

from modules.categories.api.staff_views import (
    StaffCategoryDetailView,
    StaffCategoryListView,
)

urlpatterns = [
    path("", StaffCategoryListView.as_view(), name="staff-categories"),
    path(
        "<str:code>/", StaffCategoryDetailView.as_view(), name="staff-category-detail"
    ),
]
