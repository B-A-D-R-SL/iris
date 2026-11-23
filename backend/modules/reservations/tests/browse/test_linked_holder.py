# AI contribution: 50% or more AI-generated
"""US-93 with US-36: a walk-in holder linked by invitation can browse."""

from datetime import timedelta
from typing import Any

import pytest
from rest_framework.test import APIClient

from modules.accounts import services as account_services
from modules.accounts.tests.factories import UserFactory
from modules.reservations.tests.browse.helpers import NOW, URL, _household, _listing
from modules.rules.services import publish

pytestmark = pytest.mark.django_db
EMAIL = "walk-in-holder@example.test"


def test_linked_holder_can_browse_and_unlinked_cannot(client: APIClient) -> None:
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
    linked = account_services.accept_invitation(token, "Uncommon-secret-9146!")
    _listing()
    client.force_login(linked)
    assert client.get(URL).status_code == 200

    unlinked = UserFactory(role="beneficiary")
    _household(None, channel="walk_in")
    client.force_login(unlinked)
    response = client.get(URL)
    assert response.status_code == 403
    assert response.json()["code"] == "household_not_approved"
