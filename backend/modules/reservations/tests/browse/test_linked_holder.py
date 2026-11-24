# AI contribution: 50% or more AI-generated
"""US-93 with US-36 and US-41: a walk-in holder linked by invitation uses Iris."""

from datetime import timedelta
from typing import Any

import pytest
from rest_framework.test import APIClient

from modules.accounts import services as account_services
from modules.accounts.tests.factories import UserFactory
from modules.reservations.models import Reservation
from modules.reservations.tests.browse.helpers import NOW, URL, _household, _listing
from modules.reservations.tests.factories import publish_reservation_rules
from modules.rules.services import publish

pytestmark = pytest.mark.django_db
EMAIL = "walk-in-holder@example.test"
RESERVE_URL = "/api/reservations/"  # the path in docs/03-design/api.md


def _linked_walk_in_holder() -> tuple[Any, Any]:
    """An approved walk-in file and the account its accepted invitation created."""
    admin: Any = UserFactory(role="admin", password=None)
    publish(
        "invitations",
        {"expires_after_days": 7},
        admin,
        effective_from=NOW - timedelta(days=1),
    )
    household = _household(None, channel="walk_in", email=EMAIL)
    token = account_services.create_invitation(
        EMAIL, "Walk", "In", "beneficiary", household_id=household.pk
    )
    return account_services.accept_invitation(token, "Uncommon-secret-9146!"), household


# rule: BR-HH-ACCOUNT-001
def test_linked_holder_can_browse_and_unlinked_cannot(client: APIClient) -> None:
    linked, _ = _linked_walk_in_holder()
    _listing()
    client.force_login(linked)
    assert client.get(URL).status_code == 200

    unlinked = UserFactory(role="beneficiary")
    _household(None, channel="walk_in")
    client.force_login(unlinked)
    response = client.get(URL)
    assert response.status_code == 403
    assert response.json()["code"] == "household_not_approved"


# rule: BR-HH-ACCOUNT-001
def test_linked_holder_reserves_for_the_walk_in_file(client: APIClient) -> None:
    publish_reservation_rules(NOW - timedelta(days=1))
    linked, household = _linked_walk_in_holder()
    listing = _listing(quantity_total=5, max_per_household=2)
    client.force_login(linked)

    response = client.post(
        RESERVE_URL, {"listing_id": str(listing.pk), "quantity": 1}, format="json"
    )

    assert response.status_code == 201
    reservation = Reservation.objects.get(pk=response.json()["id"])
    assert (reservation.household_id, reservation.made_by_id) == (
        household.pk,
        linked.pk,
    )
