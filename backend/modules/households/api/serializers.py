# AI contribution: 50% or more AI-generated
"""Explicit HTTP fields: never allow a client to set status, staff IDs or audit data."""

import re
from collections.abc import Mapping
from typing import Any

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from modules.households.domain.address import normalize_postal_code
from modules.households.domain.person import valid_name, validate_birth_date
from modules.households.models import Household, Member


class RejectUnknownFieldsMixin:
    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)  # type: ignore[attr-defined]
            if unknown:
                raise serializers.ValidationError(
                    {
                        key: _("This field cannot be submitted.")
                        for key in sorted(unknown)
                    }
                )
        return super().to_internal_value(data)  # type: ignore[misc, no-any-return]


class NameField(serializers.CharField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(max_length=100, trim_whitespace=True, **kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        if not valid_name(value):
            raise serializers.ValidationError(
                _("Use letters, spaces, apostrophes or hyphens.")
            )
        return value


class CanadianPhoneField(serializers.CharField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(max_length=30, **kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        digits = re.sub(r"[\s().-]", "", value)
        if digits.startswith("+"):
            correct = re.fullmatch(r"\+1\d{10}", digits)
        elif digits.startswith("1") and len(digits) == 11:
            digits = "+" + digits
            correct = re.fullmatch(r"\+1\d{10}", digits)
        elif len(digits) == 10:
            digits = "+1" + digits
            correct = re.fullmatch(r"\+1\d{10}", digits)
        else:
            correct = None
        if not correct:
            raise serializers.ValidationError(
                _("Enter a 10-digit Canadian telephone number.")
            )
        return digits


class PostalCodeField(serializers.CharField):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(max_length=8, **kwargs)

    def to_internal_value(self, data: Any) -> str:
        raw = super().to_internal_value(data)
        try:
            return normalize_postal_code(raw)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class HolderInputSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    first_name = NameField()
    last_name = NameField()
    date_of_birth = serializers.DateField()
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    phone = CanadianPhoneField()
    preferred_language = serializers.ChoiceField(
        choices=Household._meta.get_field("preferred_language").choices,
        default="fr",
    )

    def validate_date_of_birth(self, value):
        try:
            validate_birth_date(value, timezone.localdate(), holder=True)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate_email(self, value):
        return value.lower().strip() if value else None


class AddressInputSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    street_number = serializers.RegexField(
        r"^\d{1,8}[a-zA-Z]?(?:[/\-]\d{1,3})?$", max_length=10
    )
    street_name = serializers.CharField(min_length=2, max_length=120)
    unit = serializers.CharField(
        max_length=10, allow_blank=True, allow_null=True, required=False
    )
    city = serializers.CharField(max_length=80, min_length=1)
    province = serializers.ChoiceField(choices=["QC"], required=False, default="QC")
    postal_code = PostalCodeField()


class MemberInputSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    first_name = NameField()
    last_name = NameField()
    date_of_birth = serializers.DateField()
    relation = serializers.ChoiceField(
        choices=[
            relation
            for relation, _ in Member.Relation.choices
            if relation != Member.Relation.HOLDER
        ]
    )

    def validate_date_of_birth(self, value):
        try:
            validate_birth_date(value, timezone.localdate())
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class WalkInDraftInputSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    holder = HolderInputSerializer(required=False)
    address = AddressInputSerializer(required=False)
    members = MemberInputSerializer(many=True, required=False)
    identity_checked_in_person = serializers.BooleanField(required=False)

    def validate_members(self, members):
        if len(members) > 14:
            raise serializers.ValidationError(
                _("Add at most 14 people besides the holder.")
            )
        return members

    def validate_address(self, address):
        address.pop("province", None)  # fixed QC; never stored as a free-form province.
        return address


class MemberReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ("id", "first_name", "last_name", "date_of_birth", "relation")
        read_only_fields = fields


class WalkInDraftReadSerializer(serializers.ModelSerializer):
    members = MemberReadSerializer(many=True, read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    verified_by_email = serializers.EmailField(
        source="verified_by.email", read_only=True, allow_null=True
    )

    class Meta:
        model = Household
        fields = (
            "id",
            "channel",
            "status",
            "email",
            "preferred_language",
            "phone",
            "street_number",
            "street_name",
            "unit",
            "city",
            "postal_code",
            "identity_checked_in_person",
            "members",
            "created_by_email",
            "created_at",
            "updated_at",
            "verified_by_email",
            "verified_at",
        )
        read_only_fields = fields
