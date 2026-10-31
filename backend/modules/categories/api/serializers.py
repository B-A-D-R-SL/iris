# AI contribution: 50% or more AI-generated
"""Public response serialization for listing categories."""

from rest_framework import serializers

from modules.categories.models import Category


class CategorySerializer(serializers.ModelSerializer):
    """Expose public category fields without internal database IDs."""

    class Meta:
        model = Category
        fields = (
            "code",
            "name_fr",
            "name_en",
            "is_food",
            "default_value_cents",
        )
        read_only_fields = fields
