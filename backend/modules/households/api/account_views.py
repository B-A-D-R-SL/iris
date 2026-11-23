# AI contribution: 50% or more AI-generated
"""Staff endpoints for a walk-in household's Iris account (US-93).

The views check access and map errors; account_link_services checks the file
and the account, saves the link, audits and logs it.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from modules.households import account_link_services, queries
from modules.households.account_link_queries import account_link
from modules.households.api.serializers import (
    AccountLinkSerializer,
    HouseholdErrorSerializer,
    LinkAccountInputSerializer,
)
from modules.households.api.views import (
    IsIntakeWorkerOrAdmin,
    WalkInErrorHandlingMixin,
    _service_validation,
)
from modules.households.models import Household

_RESPONSES = {
    200: AccountLinkSerializer,
    400: HouseholdErrorSerializer,
    403: HouseholdErrorSerializer,
    404: HouseholdErrorSerializer,
}


class WalkInAccountView(WalkInErrorHandlingMixin, GenericAPIView):
    """Validate the body, run one account service and answer the new state."""

    permission_classes = (IsIntakeWorkerOrAdmin,)

    def _respond(
        self,
        request: Request,
        household_id: UUID,
        service: Callable[[UUID, Any], Household],
    ) -> Response:
        if queries.walk_in_for_staff(household_id, request.user) is None:
            raise Http404
        self.get_serializer(data=request.data).is_valid(raise_exception=True)
        try:
            household = service(household_id, request.user)
        except Household.DoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            raise _service_validation(exc) from exc
        return Response(AccountLinkSerializer(account_link(household)).data)


class WalkInLinkAccountView(WalkInAccountView):
    serializer_class = LinkAccountInputSerializer

    @extend_schema(
        request=LinkAccountInputSerializer,
        responses=_RESPONSES,
        tags=["staff households"],
        summary="Link the existing account that uses an approved walk-in's email",
        description=(
            "Staff first compare the person's ID with the name on the account "
            "(the detail's account block) and send identity_confirmed: true. "
            "Only an active beneficiary account without a household is linked."
        ),
    )
    def post(self, request: Request, id: UUID, *args: Any, **kwargs: Any) -> Response:
        """Link the account and return the file's new account state."""
        return self._respond(request, id, account_link_services.link_existing_account)
