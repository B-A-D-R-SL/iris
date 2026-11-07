# AI contribution: 50% or more AI-generated
"""Bounded search input and the minimal household summary for staff."""

from rest_framework import serializers

from modules.households.models import Household


class HouseholdSearchInputSerializer(serializers.Serializer):
    q = serializers.CharField(
        required=False, default="", allow_blank=True, max_length=254
    )


class HouseholdSearchResultSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(read_only=True, allow_null=True)
    last_name = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Household
        fields = (
            "id",
            "member_number",
            "first_name",
            "last_name",
            "status",
            "channel",
            "email",
            "phone",
            "street_number",
            "street_name",
            "unit",
            "city",
            "postal_code",
        )
        read_only_fields = fields
