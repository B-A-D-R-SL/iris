# AI contribution: 50% or more AI-generated
"""HTTP endpoints for accounts."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from modules.accounts.api.serializers import CurrentUserSerializer


@extend_schema(
    responses={
        200: CurrentUserSerializer,
        401: OpenApiResponse(description="Authentication required."),
    }
)
@api_view(["GET"])
def current_user(request: Request) -> Response:
    return Response(CurrentUserSerializer(request.user).data)
