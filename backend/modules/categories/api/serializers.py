# AI contribution: 50% or more AI-generated
"""Serialization for the public category list and the admin endpoints (US-35)."""

from collections.abc import Mapping

from django.utils.translation import gettext_lazy as _
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


class StaffCategorySerializer(serializers.ModelSerializer):
    """Admin view of a category (US-35): all fields, including inactive ones.

    The code is the category's stable identifier: it can be set when the
    category is created, never changed afterwards.
    """

    code = serializers.RegexField(
        r"^[a-z][a-z0-9_]*$",
        max_length=64,
        error_messages={
            "invalid": _(
                "Use lowercase letters, numbers and underscores, starting with a letter."
            )
        },
    )
    name_fr = serializers.CharField(max_length=150)
    name_en = serializers.CharField(max_length=150)
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Category
        fields = (
            "code",
            "name_fr",
            "name_en",
            "is_food",
            "default_value_cents",
            "is_active",
        )
        extra_kwargs = {"default_value_cents": {"min_value": 0, "required": True}}  # noqa: RUF012

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {
                        key: _("This field cannot be submitted.")
                        for key in sorted(unknown)
                    }
                )
        return super().to_internal_value(data)

    def validate_code(self, value: str) -> str:
        if self.instance is not None:
            raise serializers.ValidationError(_("A category code cannot be changed."))
        return value


class CategoryErrorSerializer(serializers.Serializer):
    """Error envelope shared by the category admin endpoints."""

    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
