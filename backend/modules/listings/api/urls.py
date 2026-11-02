# AI contribution: 50% or more AI-generated
"""US-33 collection route; browsing/editing remain separate stories."""

from django.urls import path

from modules.listings.api.views import PostListingView

urlpatterns = [
    path("listings/", PostListingView.as_view(), name="store-listing-create")
]
