# AI contribution: 50% or more AI-generated
"""Public HTTP endpoints for listing categories."""

from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny

from modules.categories.api.serializers import CategorySerializer
from modules.categories.queries import list_active_categories


@extend_schema(
    tags=["categories"],
    summary="List active listing categories",
    description=(
        "Public read-only endpoint. Returns active categories "
        "with French and English names."
    ),
)
class CategoryListView(generics.ListAPIView):
    """List active categories without requiring authentication."""

    serializer_class = CategorySerializer
    permission_classes = (AllowAny,)
    http_method_names = ("get", "head", "options")

    def get_queryset(self):
        """Use the module's public read interface."""
        return list_active_categories()
