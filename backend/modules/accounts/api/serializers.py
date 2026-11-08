# AI contribution: 50% or more AI-generated
"""HTTP request and response contracts for account endpoints."""

from collections.abc import Mapping
from typing import Any

from django.utils.translation import gettext_lazy as _
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


class AcceptInvitationSerializer(serializers.Serializer):
    """Accept only the secret token and a password, never account assignments."""

    token = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """Refuse identity and privilege fields instead of silently ignoring them."""
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


class InvitationAcceptedSerializer(serializers.Serializer):
    """Confirm completion without returning credentials or account information."""

    accepted = serializers.BooleanField(read_only=True)


class InvitationErrorSerializer(serializers.Serializer):
    """Document the shared error envelope used by invitation acceptance."""

    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )
