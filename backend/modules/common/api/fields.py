# AI contribution: 50% or more AI-generated
"""Normalize contact text; the pure rules enforce canonical lengths."""

from typing import Any, ClassVar

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from modules.common.domain.contact import normalize_phone, normalize_postal_code


class CanadianPhoneField(serializers.CharField):
    default_error_messages: ClassVar[dict[str, Any]] = {
        "invalid": _("Enter a 10-digit Canadian telephone number.")
    }

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                self.error_messages["invalid"], code="invalid"
            ) from exc


class PostalCodeField(serializers.CharField):
    default_error_messages: ClassVar[dict[str, Any]] = {
        "invalid": _("Enter a Canadian postal code, for example H2X 1Y4.")
    }

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        try:
            return normalize_postal_code(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                self.error_messages["invalid"], code="invalid"
            ) from exc
