# AI contribution: 50% or more AI-generated
"""Household routes under /api/: browsing (US-36) and reserving (US-41)."""

from django.urls import path

from modules.reservations.api.reserve_views import ReserveView
from modules.reservations.api.views import BrowseListingsView

urlpatterns = [
    path("listings/", BrowseListingsView.as_view(), name="listings-browse"),
    path("reservations/", ReserveView.as_view(), name="reservations-create"),
]
