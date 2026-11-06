# AI contribution: 50% or more AI-generated
"""API response contracts for notice files."""

from rest_framework import serializers


class NoticeFileLinkSerializer(serializers.Serializer):
    url = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
