# AI contribution: 50% or more AI-generated
"""URL configuration for public category endpoints."""

from django.urls import path

from modules.categories.api.views import CategoryListView

urlpatterns = [
    path("", CategoryListView.as_view(), name="categories-list"),
]
