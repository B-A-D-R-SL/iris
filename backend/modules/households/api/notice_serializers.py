# AI contribution: 50% or more AI-generated
"""Walk-in notice form fields (multipart) and the recorded notice in responses.

The input serializer checks types and normalizes the name and postal code with
the households rules; which fields a notice needs is decided by documents
(BR-DOC-001 to BR-DOC-004). Empty form fields arrive as None or "".
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.households.api.serializers import (
    NameField,
    PostalCodeField,
    RejectUnknownFieldsMixin,
)


@extend_schema_field(OpenApiTypes.BINARY)
class NoticeUploadField(serializers.FileField):
    """The scanned or photographed notice, sent as a multipart file part."""


class WalkInNoticeInputSerializer(RejectUnknownFieldsMixin, serializers.Serializer):
    member = serializers.UUIDField()
    did_not_file = serializers.BooleanField(required=False, default=False)
    did_not_file_reason = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    file = NoticeUploadField(
        required=False, allow_null=True, allow_empty_file=True, max_length=None
    )
    tax_year = serializers.IntegerField(required=False, allow_null=True)
    total_income_cents = serializers.IntegerField(required=False, allow_null=True)
    name_on_notice = NameField(required=False, allow_blank=True, allow_null=True)
    postal_code_on_notice = PostalCodeField(
        required=False, allow_blank=True, allow_null=True
    )
    notice_date = serializers.DateField(required=False, allow_null=True)
    # allow_null: an absent box is "not answered" (None), not "No".
    seen_in_person = serializers.BooleanField(required=False, allow_null=True)


class WalkInNoticeReadSerializer(serializers.Serializer):
    """The recorded notice; the private file reference is never returned."""

    id = serializers.UUIDField(read_only=True)
    member = serializers.UUIDField(source="member_id", read_only=True)
    status = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    tax_year = serializers.IntegerField(read_only=True, allow_null=True)
    total_income_cents = serializers.IntegerField(read_only=True, allow_null=True)
    name_on_notice = serializers.CharField(read_only=True)
    postal_code_on_notice = serializers.CharField(read_only=True)
    notice_date = serializers.DateField(read_only=True, allow_null=True)
    seen_in_person = serializers.BooleanField(read_only=True)
    did_not_file_reason = serializers.CharField(read_only=True)
    has_file = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
