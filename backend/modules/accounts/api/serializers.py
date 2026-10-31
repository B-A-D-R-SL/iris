# AI contribution: 50% or more AI-generated
"""Response serializers for account endpoints."""

from rest_framework import serializers

from modules.accounts.models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="get_full_name", read_only=True)
    language = serializers.ChoiceField(
        choices=User._meta.get_field("preferred_language").choices,
        source="preferred_language",
        read_only=True,
    )

    class Meta:
        model = User
        fields = ("id", "name", "role", "store", "language")
        read_only_fields = fields
