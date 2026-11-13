# AI contribution: 50% or more AI-generated
"""Household routes under /api/: browsing now, reserving with US-41."""

from django.urls import path

from modules.reservations.api.views import BrowseListingsView

urlpatterns = [
    path("listings/", BrowseListingsView.as_view(), name="listings-browse"),
]
