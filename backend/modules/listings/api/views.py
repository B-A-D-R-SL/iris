# AI contribution: 50% or more AI-generated
"""Thin, session-authenticated boundary for US-33 and US-34."""

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import (
    APIException,
    NotAuthenticated,
    ParseError,
    PermissionDenied,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from modules.listings import queries, services
from modules.listings.api.permissions import IsStorePoster
from modules.listings.api.serializers import (
    NewListingSerializer,
    PostedListingSerializer,
    PostingCategorySerializer,
    PostingErrorSerializer,
)
from modules.listings.domain.posting import ListingInput, SafetyRulesInvalid
from modules.listings.permissions import assigned_store_id


class PostingDependencyUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "posting_unavailable"
    default_detail = _("Posting is temporarily unavailable.")


def posting_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, ValidationError):
        fields = response.data
        if not isinstance(fields, dict):
            fields = {"non_field_errors": fields}
        response.data = {
            "code": "validation_error",
            "message": str(_("Check the highlighted fields.")),
            "fields": {
                key: value if isinstance(value, list) else [value]
                for key, value in fields.items()
            },
        }
    else:
        response.data = {
            "code": getattr(exc, "default_code", "permission_denied"),
            "message": str(response.data.get("detail", _("The request was refused."))),
            "fields": {},
        }
    return response


class PostListingView(GenericAPIView):
    serializer_class = NewListingSerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsStorePoster,)

    def get_exception_handler(self) -> Any:
        return posting_exception_handler

    def handle_exception(self, exc: Exception) -> Response:
        """Record early POST refusals; service failures already have their events."""
        if self.request.method == "POST":
            if isinstance(exc, (PermissionDenied, NotAuthenticated)):
                services.log_post_refused("store_access_denied")
            elif isinstance(
                exc, (ValidationError, ParseError, UnsupportedMediaType)
            ) and not isinstance(exc.__cause__, DjangoValidationError):
                # Chained Django validation errors were already logged by the service.
                services.log_post_refused("listing_validation_failed")
        return super().handle_exception(exc)

    @extend_schema(
        operation_id="store_listings_create",
        summary="Post a listing for the signed-in user's active store",
        tags=["store listings"],
        responses={
            201: PostedListingSerializer,
            400: PostingErrorSerializer,
            403: PostingErrorSerializer,
            503: PostingErrorSerializer,
        },
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        assigned_store = assigned_store_id(request.user)
        store = values.pop("store", assigned_store)
        if store != assigned_store:
            raise PermissionDenied(_("You can only post for your own store."))
        photo = values.pop("photo", None)
        try:
            listing = services.post_listing(
                store, request.user, ListingInput(**values), photo=photo
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        except services.PostingUnavailableError:
            raise PostingDependencyUnavailable() from None
        return Response(
            PostedListingSerializer(listing).data, status=status.HTTP_201_CREATED
        )


class PostingCategoriesView(GenericAPIView):
    """Categories for the posting form; banned ones (US-34) are left out."""

    serializer_class = PostingCategorySerializer
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsStorePoster,)
    http_method_names = ("get", "head", "options")

    def get_exception_handler(self) -> Any:
        return posting_exception_handler

    @extend_schema(
        operation_id="store_listings_categories_list",
        summary="List the categories the signed-in store can post in",
        tags=["store listings"],
        responses={
            200: PostingCategorySerializer(many=True),
            403: PostingErrorSerializer,
            503: PostingErrorSerializer,
        },
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        try:
            categories = queries.categories_for_posting(at=timezone.now())
        except SafetyRulesInvalid:
            services.log_posting_unavailable("safety_rules_invalid")
            raise PostingDependencyUnavailable() from None
        if categories is None:
            services.log_posting_unavailable("listing_rules_missing")
            raise PostingDependencyUnavailable()
        return Response(PostingCategorySerializer(categories, many=True).data)
