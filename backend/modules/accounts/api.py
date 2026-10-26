# AI contribution: 50% or more AI-generated
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from modules.accounts.models import User


class CurrentUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="get_full_name", read_only=True)
    language = serializers.CharField(source="preferred_language", read_only=True)

    class Meta:
        model = User
        fields = ("id", "name", "role", "store", "language")
        read_only_fields = fields


@extend_schema(
    responses={
        200: CurrentUserSerializer,
        401: OpenApiResponse(description="Authentication required."),
    }
)
@api_view(["GET"])
def current_user(request: Request) -> Response:
    return Response(CurrentUserSerializer(request.user).data)
