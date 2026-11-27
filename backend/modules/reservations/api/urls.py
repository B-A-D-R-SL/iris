# AI contribution: 50% or more AI-generated
"""Household routes under /api/: browsing (US-36), reserving (US-41) and history (US-48)."""

from django.urls import path

from modules.reservations.api.history_views import HouseholdHistoryView
from modules.reservations.api.reserve_views import ReserveView
from modules.reservations.api.views import BrowseListingsView

urlpatterns = [
    path("listings/", BrowseListingsView.as_view(), name="listings-browse"),
    path("reservations/", ReserveView.as_view(), name="reservations-create"),
    path("reservations/me/", HouseholdHistoryView.as_view(), name="reservations-mine"),
]
