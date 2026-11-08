# AI contribution: 50% or more AI-generated
"""Bounded search input and the minimal household summary for staff."""

from rest_framework import serializers

from modules.households.models import Household
from modules.households.policies import can_resume_walk_in


class HouseholdSearchInputSerializer(serializers.Serializer):
    q = serializers.CharField(
        required=False, default="", allow_blank=True, max_length=254
    )


class HouseholdSearchResultSerializer(serializers.ModelSerializer):
    """Expose minimal household fields and the server-authorized resume action."""

    first_name = serializers.CharField(read_only=True, allow_null=True)
    last_name = serializers.CharField(read_only=True, allow_null=True)
    can_resume = serializers.SerializerMethodField()

    def get_can_resume(self, household: Household) -> bool:
        """Fail closed when serialization has no authenticated request context."""
        request = self.context.get("request")
        return can_resume_walk_in(household, request.user if request else None)

    class Meta:
        model = Household
        fields = (
            "id",
            "member_number",
            "first_name",
            "last_name",
            "status",
            "channel",
            "can_resume",
            "email",
            "phone",
            "street_number",
            "street_name",
            "unit",
            "city",
            "postal_code",
        )
        read_only_fields = fields
