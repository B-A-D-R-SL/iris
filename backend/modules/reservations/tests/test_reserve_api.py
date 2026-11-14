# AI contribution: 50% or more AI-generated
"""POST /api/reservations/ (US-41) through the API and the database.

Allowed: an active beneficiary whose own household is approved. Refused:
signed out (401), every other role and a household that is not approved
(403), bad input (400), and each business refusal with its own code.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.reservations.tests.factories import (
    ReservationFactory,
    approved_household,
    open_listing,
    publish_reservation_rules,
)
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 9, 15, tzinfo=UTC)
URL = "/api/reservations/"  # the path in docs/03-design/api.md


@pytest.fixture(autouse=True)
def setup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    publish_reservation_rules(NOW - timedelta(days=1))


@pytest.fixture
def listing() -> Any:
    return open_listing(NOW, quantity_total=5, max_per_household=2)


@pytest.fixture
def household() -> Any:
    return approved_household(NOW)


def _client(user: Any = None, language: str = "en") -> APIClient:
    client = APIClient(HTTP_ACCEPT_LANGUAGE=language)
    if user is not None:
        client.force_login(user)
    return client


def _post(client: APIClient, listing: Any, quantity: Any = 1) -> Any:
    return client.post(
        URL, {"listing_id": str(listing.pk), "quantity": quantity}, format="json"
    )


# Main path, acceptance criteria 1 and 4: through the API into the database.
def test_approved_household_reserves_and_gets_its_code(
    household: Any, listing: Any
) -> None:
    response = _post(_client(household.holder), listing, 2)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {
        "id",
        "listing_id",
        "quantity",
        "pickup_code",
        "status",
        "created_at",
    }
    assert body["listing_id"] == str(listing.pk)
    assert body["quantity"] == 2
    assert body["status"] == "reserved"
    assert len(body["pickup_code"]) == 6
    listing.refresh_from_db()
    assert listing.quantity_reserved == 2
    reservation = household.reservations.get()
    assert reservation.pickup_code == body["pickup_code"]


def test_quantity_defaults_to_one(household: Any, listing: Any) -> None:
    response = _client(household.holder).post(
        URL, {"listing_id": str(listing.pk)}, format="json"
    )
    assert response.status_code == 201
    assert response.json()["quantity"] == 1


# --- Roles ---------------------------------------------------------------------


def test_signed_out_is_refused(listing: Any) -> None:
    response = _post(_client(), listing)
    assert response.status_code == 401
    assert response.json()["message"] == "Sign in to reserve."


@pytest.mark.parametrize(
    "role", ["store_staff", "store_manager", "intake_worker", "admin"]
)
def test_other_roles_are_refused(role: str, listing: Any) -> None:
    # Store roles must belong to a store (database constraint).
    store = StoreFactory() if role.startswith("store_") else None
    response = _post(_client(UserFactory(role=role, store=store)), listing)
    assert response.status_code == 403
    listing.refresh_from_db()
    assert listing.quantity_reserved == 0


def test_beneficiary_without_a_household_is_refused(listing: Any) -> None:
    response = _post(_client(UserFactory(role="beneficiary")), listing)
    assert response.status_code == 403
    assert response.json()["code"] == "household_not_approved"


# rule: BR-RES-006 acceptance criterion 3.
@pytest.mark.parametrize(
    "changes",
    [{"status": "suspended"}, {"status": "renewal_needed"}, {"expires_at": NOW}],
)
def test_household_that_is_not_approved_is_refused(
    changes: dict[str, Any], listing: Any
) -> None:
    household = approved_household(NOW, **changes)
    response = _post(_client(household.holder, "fr"), listing)
    assert response.status_code == 403
    assert response.json() == {
        "code": "household_not_approved",
        "message": "Seuls les foyers approuvés peuvent réserver.",
        "fields": {},
    }


def test_inactive_beneficiary_is_refused(household: Any, listing: Any) -> None:
    household.holder.is_active = False
    household.holder.save()
    response = _post(_client(household.holder), listing)
    assert response.status_code in (401, 403)


def test_only_post_is_allowed(household: Any) -> None:
    response = _client(household.holder).get(URL)
    assert response.status_code == 405


# --- Bad input --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"listing_id": "not-a-uuid", "quantity": 1}, "listing_id"),
        ({"quantity": 1}, "listing_id"),
        ({"listing_id": str(uuid.uuid4()), "quantity": 0}, "quantity"),
        ({"listing_id": str(uuid.uuid4()), "quantity": 11}, "quantity"),
        ({"listing_id": str(uuid.uuid4()), "quantity": "two"}, "quantity"),
    ],
)
def test_bad_input_is_refused(household: Any, payload: dict, field: str) -> None:
    response = _client(household.holder).post(URL, payload, format="json")
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert list(body["fields"]) == [field]


# --- Business refusals -------------------------------------------------------------


def test_sold_out_says_so(household: Any, listing: Any) -> None:
    listing.quantity_reserved = 5
    listing.save()
    response = _post(_client(household.holder), listing)
    assert response.status_code == 409
    assert response.json() == {
        "code": "sold_out",
        "message": "Sorry, this listing is sold out.",
        "fields": {},
    }


def test_sold_out_in_french(household: Any, listing: Any) -> None:
    listing.quantity_reserved = 5
    listing.save()
    response = _post(_client(household.holder, "fr"), listing)
    assert response.json()["message"] == "Désolé, cette offre est épuisée."


# rule: BR-RES-007
def test_over_the_listing_max_is_refused(household: Any, listing: Any) -> None:
    response = _post(_client(household.holder), listing, 3)
    assert response.status_code == 400
    assert response.json()["code"] == "quantity_over_listing_limit"


# rule: BR-RES-008
def test_fourth_active_reservation_is_refused(household: Any, listing: Any) -> None:
    for _ in range(3):
        ReservationFactory(household=household, made_by=household.holder)
    response = _post(_client(household.holder), listing)
    assert response.status_code == 409
    assert response.json()["code"] == "too_many_active_reservations"


def test_listing_that_is_gone_is_404(household: Any) -> None:
    gone = open_listing(NOW, status="closed")
    response = _post(_client(household.holder), gone)
    assert response.status_code == 404
    assert response.json()["code"] == "listing_not_available"


def test_unknown_listing_is_404(household: Any) -> None:
    response = _client(household.holder).post(
        URL, {"listing_id": str(uuid.uuid4())}, format="json"
    )
    assert response.status_code == 404
