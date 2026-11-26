# AI contribution: 50% or more AI-generated
"""HTTP request and response contracts for account endpoints."""

from collections.abc import Mapping
from typing import Any

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from modules.accounts import services
from modules.accounts.models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="get_full_name", read_only=True)
    language = serializers.ChoiceField(
        choices=services.LANGUAGE_CHOICES,
        source="preferred_language",
        read_only=True,
    )

    class Meta:
        model = User
        fields = ("id", "name", "role", "store", "language")
        read_only_fields = fields


class StrictSerializer(serializers.Serializer):
    """Refuse fields the endpoint does not accept instead of silently ignoring them."""

    def to_internal_value(self, data: Any) -> dict[str, Any]:
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


class LanguageChoiceSerializer(StrictSerializer):
    """US-08: the only account field a user changes here is their language."""

    language = serializers.ChoiceField(
        choices=services.LANGUAGE_CHOICES,
        error_messages={"invalid_choice": services.INVALID_LANGUAGE},
    )

    # PATCH /api/me/ always validates the whole body, so this serializer is never
    # partial. drf-spectacular marks PATCH bodies partial by setting this flag,
    # which would publish `language` as optional; ignoring it keeps the schema
    # in step with the validation.
    @property
    def partial(self) -> bool:
        return False

    @partial.setter
    def partial(self, value: bool) -> None:
        pass


class AcceptInvitationSerializer(StrictSerializer):
    """Accept only the secret token and a password, never account assignments."""

    token = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, style={"input_type": "password"}
    )


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
