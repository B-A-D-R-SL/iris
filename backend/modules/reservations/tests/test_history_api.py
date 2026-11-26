# AI contribution: 50% or more AI-generated
"""GET /api/reservations/me/ (US-48) through the API and the database.

Acceptance criterion: each reservation shows its date, store, item, quantity and
status. Allowed: an active beneficiary, for the household they hold, whatever
its status. Refused: signed out (401) and every other role (403). Edge cases:
an unknown status filter (400), a page past the end (404), no household or an
anonymized one (empty list), and another household's rows (never shown).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.reservations.models import ReservationStatus
from modules.reservations.tests.factories import (
    ReservationFactory,
    approved_household,
    open_listing,
)
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

# Wednesday 25 November 2026, 15:00 in Montreal.
NOW = datetime(2026, 11, 25, 20, tzinfo=UTC)
URL = "/api/reservations/me/"  # the path in docs/03-design/api.md


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every request in this file happens at NOW."""
    monkeypatch.setattr(timezone, "now", lambda: NOW)


@pytest.fixture
def household() -> Any:
    """An approved household whose holder signs in."""
    return approved_household(NOW)


def _client(user: Any = None, language: str = "en") -> APIClient:
    """An API client, signed in as ``user`` when one is given."""
    client = APIClient(HTTP_ACCEPT_LANGUAGE=language)
    if user is not None:
        client.force_login(user)
    return client


def _reserve(household: Any, *, starts_in: timedelta, **kwargs: Any) -> Any:
    """A reservation of ``household``; its two-hour pickup starts at NOW + ``starts_in``.

    ``store``, ``title`` and ``pickup_end`` go to the listing; every other keyword
    to the reservation.
    """
    listing_values = {
        key: kwargs.pop(key)
        for key in ("store", "title", "pickup_end")
        if key in kwargs
    }
    listing = open_listing(NOW, pickup_start=NOW + starts_in, **listing_values)
    return ReservationFactory(
        listing=listing, household=household, made_by=household.holder, **kwargs
    )


def _titles(response: Any) -> list[str]:
    """The item titles of one page, in the order the API sent them."""
    return [entry["title"] for entry in response.json()["results"]]


# --- Acceptance criterion: date, store, item, quantity, status -------------------


# rule: BR-RES-012
def test_picked_up_reservation_shows_date_store_item_quantity_and_status(
    household: Any,
) -> None:
    """A pickup lists its window, pickup time, store, item, quantity and status."""
    store: Any = StoreFactory(name="Épicerie du Quartier", street_number="1234")
    reservation = _reserve(
        household,
        starts_in=-timedelta(days=1, hours=3),
        store=store,
        title="Légumes racines",
        quantity=2,
        status=ReservationStatus.PICKED_UP,
        picked_up_at=NOW - timedelta(days=1, hours=2),
    )

    response = _client(household.holder).get(URL)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0] == {
        "id": str(reservation.pk),
        "status": "picked_up",
        "upcoming": False,
        "title": "Légumes racines",
        "unit": "item",
        "quantity": 2,
        "store": {
            "id": str(store.pk),
            "name": "Épicerie du Quartier",
            "street_number": "1234",
            "street_name": "rue Exemple",
            "unit": None,
            "city": "Montréal",
            "postal_code": "H2X 1Y4",
        },
        "pickup_start": "2026-11-24T17:00:00Z",
        "pickup_end": "2026-11-24T19:00:00Z",
        "picked_up_at": "2026-11-24T18:00:00Z",
        # A past code can no longer be used, so it is not sent.
        "pickup_code": None,
    }


# rule: BR-RES-012
@pytest.mark.parametrize("reservation_status", ReservationStatus.values)
def test_every_status_is_listed_with_its_own_value(
    household: Any, reservation_status: str
) -> None:
    """Each of the five statuses reaches the screen unchanged."""
    _reserve(household, starts_in=-timedelta(days=2), status=reservation_status)

    response = _client(household.holder).get(URL)

    assert [entry["status"] for entry in response.json()["results"]] == [
        reservation_status
    ]


# rule: BR-RES-012
def test_upcoming_reservation_comes_first_with_its_pickup_code(household: Any) -> None:
    """An upcoming reservation is listed first and keeps its code; a past one has none."""
    _reserve(
        household,
        starts_in=-timedelta(days=1),
        title="Yogourts",
        status=ReservationStatus.CANCELLED_BY_STORE,
    )
    upcoming = _reserve(household, starts_in=timedelta(hours=1), title="Pains")

    response = _client(household.holder).get(URL)

    first, second = response.json()["results"]
    assert (first["title"], first["upcoming"]) == ("Pains", True)
    assert first["pickup_code"] == upcoming.pickup_code
    assert first["picked_up_at"] is None
    assert (second["title"], second["upcoming"], second["pickup_code"]) == (
        "Yogourts",
        False,
        None,
    )


def test_listing_closed_after_the_reservation_still_shows(household: Any) -> None:
    """Closing the listing later does not remove it from the household's history."""
    reservation = _reserve(
        household, starts_in=-timedelta(days=3), status=ReservationStatus.PICKED_UP
    )
    reservation.listing.status = "closed"
    reservation.listing.save(update_fields=["status"])

    response = _client(household.holder).get(URL)

    assert _titles(response) == [reservation.listing.title]


# --- Ownership and file status -------------------------------------------------


# rule: BR-RES-011
def test_another_households_reservations_are_never_shown(household: Any) -> None:
    """The household comes from the signed-in user, so others' rows never appear."""
    _reserve(household, starts_in=timedelta(hours=2), title="Mine")
    _reserve(approved_household(NOW), starts_in=timedelta(hours=3), title="Theirs")

    response = _client(household.holder).get(URL)

    assert _titles(response) == ["Mine"]


# rule: BR-RES-011
@pytest.mark.parametrize(
    "file_values",
    [
        {"status": "suspended"},
        {"status": "renewal_needed"},
        # Still saved as approved, but expired: browse and reserve refuse it.
        {"expires_at": NOW - timedelta(days=1)},
    ],
    ids=["suspended", "renewal_needed", "expired"],
)
def test_household_that_cannot_reserve_still_sees_its_history(
    file_values: dict[str, Any],
) -> None:
    """Suspended, expired and renewal-needed files still see what they received."""
    household = approved_household(NOW, **file_values)
    _reserve(
        household, starts_in=-timedelta(days=5), status=ReservationStatus.PICKED_UP
    )

    response = _client(household.holder).get(URL)

    assert response.status_code == 200
    assert response.json()["count"] == 1


# rule: BR-RES-011
def test_beneficiary_without_a_household_gets_an_empty_list() -> None:
    """An account that holds no household has no history, not an error."""
    response = _client(UserFactory(role="beneficiary")).get(URL)

    assert response.status_code == 200
    assert response.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }


# rule: BR-RES-011
def test_anonymized_household_gets_an_empty_list(household: Any) -> None:
    """An anonymized file's reservations are no longer shown to its old account."""
    _reserve(
        household, starts_in=-timedelta(days=5), status=ReservationStatus.PICKED_UP
    )
    household.anonymized_at = NOW - timedelta(hours=1)
    household.save(update_fields=["anonymized_at"])

    response = _client(household.holder).get(URL)

    assert response.status_code == 200
    assert response.json()["count"] == 0


# --- Roles -----------------------------------------------------------------------


# rule: BR-RES-011
def test_signed_out_is_refused() -> None:
    """Signed out gets 401 with a fixed message."""
    response = _client().get(URL)

    assert response.status_code == 401
    assert response.json() == {
        "code": "not_authenticated",
        "message": "Sign in to see your reservations.",
        "fields": {},
    }


def test_refusal_is_translated_to_french() -> None:
    """The refusal follows the request's language."""
    response = _client(language="fr").get(URL)

    assert response.status_code == 401
    assert response.json()["message"] == "Connectez-vous pour voir vos réservations."


# rule: BR-RES-011
@pytest.mark.parametrize(
    "role", ["store_staff", "store_manager", "intake_worker", "admin"]
)
def test_other_roles_are_refused(role: str, household: Any) -> None:
    """Staff and store accounts get 403: they have no household history."""
    _reserve(household, starts_in=timedelta(hours=1))
    # Store roles must belong to a store (database constraint).
    store = StoreFactory() if role.startswith("store_") else None

    response = _client(UserFactory(role=role, store=store)).get(URL)

    assert response.status_code == 403
    assert response.json() == {
        "code": "permission_denied",
        "message": "Only household accounts have reservations.",
        "fields": {},
    }


def test_the_history_cannot_be_written(household: Any) -> None:
    """The history is read-only: POST gets 405."""
    response = _client(household.holder).post(URL, {}, format="json")

    assert response.status_code == 405
    assert response.json()["message"] == "Reservations can only be read here."


# --- Filters, paging and headers ------------------------------------------------


def test_status_filter_keeps_that_status_only(household: Any) -> None:
    """?status=picked_up leaves out every other status."""
    _reserve(household, starts_in=timedelta(hours=1), title="Pains")
    _reserve(
        household,
        starts_in=-timedelta(days=1),
        title="Légumes",
        status=ReservationStatus.PICKED_UP,
    )

    response = _client(household.holder).get(URL, {"status": "picked_up"})

    assert _titles(response) == ["Légumes"]


@pytest.mark.parametrize("value", ["delivered", "PICKED_UP", "picked up"])
def test_unknown_status_filter_is_refused(household: Any, value: str) -> None:
    """An unknown status gets 400 with the field named and the accepted values."""
    response = _client(household.holder).get(URL, {"status": value})

    assert response.status_code == 400
    assert response.json() == {
        "code": "validation_error",
        "message": "Check the highlighted fields.",
        "fields": {
            "status": [
                (
                    "Enter one of reserved, picked_up, cancelled, cancelled_by_store "
                    "or no_show."
                )
            ]
        },
    }


def test_twenty_a_page_without_repeats(household: Any) -> None:
    """21 reservations make a page of 20 and a page of 1, each row once."""
    for day in range(21):
        _reserve(
            household,
            starts_in=-timedelta(days=day + 1),
            status=ReservationStatus.PICKED_UP,
        )
    client = _client(household.holder)

    first = client.get(URL).json()
    second = client.get(URL, {"page": 2}).json()

    assert first["count"] == 21
    assert len(first["results"]) == 20
    assert first["next"] is not None
    assert len(second["results"]) == 1
    seen = [entry["id"] for entry in first["results"] + second["results"]]
    assert len(set(seen)) == 21


def test_page_past_the_end_is_not_found(household: Any) -> None:
    """A page that does not exist gets 404 with a fixed message."""
    response = _client(household.holder).get(URL, {"page": 2})

    assert response.status_code == 404
    assert response.json()["message"] == "This page of reservations does not exist."


def test_page_with_pickup_codes_is_never_cached(household: Any) -> None:
    """Pickup codes are never cached or sent on in a referrer."""
    response = _client(household.holder).get(URL)

    assert response["Cache-Control"] == "private, no-store"
    assert response["Referrer-Policy"] == "no-referrer"


def test_queries_do_not_grow_with_the_page(household: Any) -> None:
    """Seven rows take as many queries as one: no query per listing or store."""
    client = _client(household.holder)
    _reserve(household, starts_in=-timedelta(days=1), status="picked_up")
    with CaptureQueriesContext(connection) as one_row:
        client.get(URL)
    for day in range(2, 8):
        _reserve(household, starts_in=-timedelta(days=day), status="picked_up")
    with CaptureQueriesContext(connection) as seven_rows:
        response = client.get(URL)

    assert response.json()["count"] == 7
    assert len(seven_rows) == len(one_row)


# --- Pages stay consistent while time passes ----------------------------------


# rule: BR-RES-012
def test_a_window_ending_between_pages_never_repeats_or_skips_a_row(
    household: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Page 2 keeps page 1's order, although a long window ended in between."""
    _reserve(
        household,
        starts_in=-timedelta(days=30),
        pickup_end=NOW + timedelta(minutes=1),
        title="Long window",
    )
    for day in range(21):
        _reserve(
            household,
            starts_in=-timedelta(days=day + 1),
            status=ReservationStatus.PICKED_UP,
        )
    client = _client(household.holder)

    first = client.get(URL).json()
    monkeypatch.setattr(timezone, "now", lambda: NOW + timedelta(minutes=2))
    second = client.get(first["next"]).json()

    assert first["results"][0]["title"] == "Long window"
    assert "as_of=2026-11-25T20%3A00%3A00Z" in first["next"]
    seen = [entry["id"] for entry in first["results"] + second["results"]]
    assert len(seen) == 22
    assert len(set(seen)) == 22


# rule: BR-RES-012
def test_pickup_codes_follow_the_current_time_on_later_pages(
    household: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A row still upcoming at page 1's time has no code once its window ended."""
    _reserve(household, starts_in=-timedelta(hours=2), title="Ended")
    monkeypatch.setattr(timezone, "now", lambda: NOW + timedelta(minutes=5))

    response = _client(household.holder).get(URL, {"as_of": "2026-11-25T20:00:00Z"})

    (entry,) = response.json()["results"]
    assert (entry["title"], entry["upcoming"], entry["pickup_code"]) == (
        "Ended",
        False,
        None,
    )


def test_a_future_as_of_counts_as_now(household: Any) -> None:
    """A time after now cannot reorder the list: the next link carries now."""
    for day in range(21):
        _reserve(
            household,
            starts_in=-timedelta(days=day + 1),
            status=ReservationStatus.PICKED_UP,
        )

    response = _client(household.holder).get(URL, {"as_of": "2030-01-01T00:00:00Z"})

    assert "as_of=2026-11-25T20%3A00%3A00Z" in response.json()["next"]


def test_invalid_as_of_is_refused(household: Any) -> None:
    """A value that is not a date and time gets 400 with the field named."""
    response = _client(household.holder).get(URL, {"as_of": "yesterday"})

    assert response.status_code == 400
    assert response.json()["fields"] == {
        "as_of": ["Enter a date and time, as in the next page link."]
    }
