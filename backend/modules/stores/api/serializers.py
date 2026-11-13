# AI contribution: 50% or more AI-generated
"""HTTP types for partner applications; the service decides and saves."""

import re
from collections.abc import Mapping
from datetime import UTC
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from modules.stores.models import (
    CANADIAN_PHONE_PATTERN,
    NAME_PATTERN,
    NEQ_PATTERN,
    POSTAL_CODE_PATTERN,
    STREET_NUMBER_PATTERN,
    ApplicationStatus,
    BusinessType,
    DonationFrequency,
    PartnerApplication,
)

# Wording from docs/02-requirements/forms-and-fields.md (partner application form).
MESSAGES = {
    "business_name": _("Enter the business name (2 to 150 characters)."),
    "business_type": _("Choose a business type."),
    "neq": _("The NEQ has exactly 10 digits. You can also leave this field empty."),
    "website": _("Enter a web address like example.ca."),
    "street_number": _("Enter a street number like 1234 or 1234A."),
    "street_name": _("Enter the street (2 to 120 characters)."),
    "unit": _("Enter at most 10 characters."),
    "city": _("Enter the city (at most 80 characters)."),
    "postal_code": _("Enter a postal code like H2X 1Y4."),
    "name": _(
        "Enter a name of 1 to 100 letters; spaces, apostrophes and hyphens are allowed."
    ),
    "contact_role": _("Enter at most 100 characters."),
    "contact_email": _("Enter an email like name@example.ca."),
    "contact_phone": _("Enter a 10-digit number, for example (514) 555-0123."),
    "goods_categories": _("Choose at least one type of goods."),
    "expected_frequency": _("Choose how often you expect to donate."),
    "opening_hours": _("Enter the opening hours (at most 300 characters)."),
    "message": _("Enter at most 1,000 characters."),
    "consent_contact": _("Tick this box to send the application."),
}

# Every way a field can fail shows the same short message saying how to fix it.
ERROR_KEYS = (
    "required",
    "null",
    "blank",
    "invalid",
    "max_length",
    "min_length",
    "invalid_choice",
    "not_a_list",
    "empty",
    "max_string_length",
    "surrogate_characters_not_allowed",
)
_URL = URLValidator(schemes=["http", "https"])


def _errors(message: Promise) -> dict[str, Promise]:
    return dict.fromkeys(ERROR_KEYS, message)


def _text(message: Promise, *, optional: bool = False, **kwargs: Any) -> Any:
    if optional:
        kwargs.update(required=False, allow_blank=True, allow_null=True)
    return serializers.CharField(error_messages=_errors(message), **kwargs)


def _matches(pattern: str, value: str, message: Promise) -> str:
    if not re.fullmatch(pattern, value):
        raise serializers.ValidationError(message)
    return value


def _blank_to_none(value: str | None) -> str | None:
    return value or None


class PartnerApplicationSerializer(serializers.Serializer):
    """Submitted partner form; field rules from forms-and-fields.md."""

    business_name = _text(MESSAGES["business_name"], min_length=2, max_length=150)
    business_type = serializers.ChoiceField(
        choices=BusinessType.choices, error_messages=_errors(MESSAGES["business_type"])
    )
    neq = _text(MESSAGES["neq"], optional=True, max_length=10)
    website = _text(MESSAGES["website"], optional=True, max_length=200)
    street_number = _text(MESSAGES["street_number"], max_length=10)
    street_name = _text(MESSAGES["street_name"], min_length=2, max_length=120)
    unit = _text(MESSAGES["unit"], optional=True, max_length=10)
    city = _text(MESSAGES["city"], max_length=80)
    postal_code = _text(MESSAGES["postal_code"], max_length=7)
    contact_first_name = _text(MESSAGES["name"], max_length=100)
    contact_last_name = _text(MESSAGES["name"], max_length=100)
    contact_role = _text(MESSAGES["contact_role"], optional=True, max_length=100)
    contact_email = serializers.EmailField(
        max_length=254, error_messages=_errors(MESSAGES["contact_email"])
    )
    contact_phone = _text(MESSAGES["contact_phone"], max_length=16)
    goods_categories = serializers.ListField(
        child=_text(MESSAGES["goods_categories"], max_length=64),
        allow_empty=False,
        max_length=50,
        error_messages=_errors(MESSAGES["goods_categories"]),
    )
    expected_frequency = serializers.ChoiceField(
        choices=DonationFrequency.choices,
        error_messages=_errors(MESSAGES["expected_frequency"]),
    )
    opening_hours = _text(MESSAGES["opening_hours"], max_length=300)
    message = _text(MESSAGES["message"], optional=True, max_length=1000)
    consent_contact = serializers.BooleanField(
        error_messages=_errors(MESSAGES["consent_contact"])
    )

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

    def validate_neq(self, value: str | None) -> str | None:
        value = _blank_to_none(value)
        return value and _matches(NEQ_PATTERN, value, MESSAGES["neq"])

    def validate_website(self, value: str | None) -> str | None:
        value = _blank_to_none(value)
        if value is None:
            return None
        if not re.match(r"^https?://", value, re.IGNORECASE):
            value = f"https://{value}"
        try:
            _URL(value)
        except DjangoValidationError:
            raise serializers.ValidationError(MESSAGES["website"]) from None
        return value

    def validate_street_number(self, value: str) -> str:
        return _matches(STREET_NUMBER_PATTERN, value, MESSAGES["street_number"])

    def validate_unit(self, value: str | None) -> str | None:
        return _blank_to_none(value)

    def validate_postal_code(self, value: str) -> str:
        _matches(POSTAL_CODE_PATTERN, value, MESSAGES["postal_code"])
        compact = value.replace(" ", "").upper()
        return f"{compact[:3]} {compact[3:]}"

    def validate_contact_first_name(self, value: str) -> str:
        return _matches(NAME_PATTERN, value, MESSAGES["name"])

    def validate_contact_last_name(self, value: str) -> str:
        return _matches(NAME_PATTERN, value, MESSAGES["name"])

    def validate_contact_role(self, value: str | None) -> str | None:
        return _blank_to_none(value)

    def validate_contact_email(self, value: str) -> str:
        return value.lower()

    def validate_contact_phone(self, value: str) -> str:
        return _matches(CANADIAN_PHONE_PATTERN, value, MESSAGES["contact_phone"])

    def validate_goods_categories(self, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))  # drop repeats, keep the chosen order

    def validate_message(self, value: str | None) -> str | None:
        return _blank_to_none(value)

    def validate_consent_contact(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError(MESSAGES["consent_contact"])
        return value


class SubmittedPartnerApplicationSerializer(serializers.ModelSerializer):
    """What the applicant gets back; no personal data is echoed."""

    status = serializers.CharField()
    # API convention: datetimes in UTC (docs/03-design/api.md).
    created_at = serializers.DateTimeField(default_timezone=UTC)

    class Meta:
        model = PartnerApplication
        fields = ("id", "status", "created_at")
        read_only_fields = fields


class PartnerApplicationErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField())
    )


class StaffPartnerApplicationSerializer(serializers.ModelSerializer):
    """An application as the admin reviews it (US-13)."""

    # API convention: datetimes in UTC (docs/03-design/api.md).
    created_at = serializers.DateTimeField(default_timezone=UTC)
    decided_at = serializers.DateTimeField(default_timezone=UTC, allow_null=True)
    can_decide = serializers.SerializerMethodField()

    def get_can_decide(self, application: PartnerApplication) -> bool:
        """Expose the service's decision rule; an absent request denies availability."""
        from modules.stores.services import can_decide_application

        request = self.context.get("request")
        return can_decide_application(application, getattr(request, "user", None))

    class Meta:
        model = PartnerApplication
        fields = (
            "id",
            "status",
            "can_decide",
            "business_name",
            "business_type",
            "neq",
            "website",
            "street_number",
            "street_name",
            "unit",
            "city",
            "postal_code",
            "contact_first_name",
            "contact_last_name",
            "contact_role",
            "contact_email",
            "contact_phone",
            "goods_categories",
            "expected_frequency",
            "opening_hours",
            "message",
            "language",
            "decision_reason",
            "decided_at",
            "created_at",
        )
        read_only_fields = fields


class StaffApplicationFilterSerializer(serializers.Serializer):
    """Query string of the review list; status is optional."""

    status = serializers.ChoiceField(
        choices=ApplicationStatus.choices,
        required=False,
        error_messages={"invalid_choice": _("Choose submitted, approved or rejected.")},
    )


class RejectApplicationSerializer(serializers.Serializer):
    """Rejection body; the service checks the length and blank reasons."""

    reason = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
        error_messages={"required": _("Enter a reason of at most 500 characters.")},
    )
