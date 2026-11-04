# AI contribution: 50% or more AI-generated
"""Store listing routes; browsing/editing remain separate stories."""

from django.urls import path

from modules.listings.api.views import PostingCategoriesView, PostListingView

urlpatterns = [
    path("listings/", PostListingView.as_view(), name="store-listing-create"),
    path(
        "listings/categories/",
        PostingCategoriesView.as_view(),
        name="store-listing-categories",
    ),
]
