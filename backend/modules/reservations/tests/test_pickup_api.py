# AI contribution: 50% or more AI-generated
"""US-44 HTTP checks for /api/store/pickups/: every role and every refusal."""

from collections.abc import Callable
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.reservations.api.pickup_views import REFUSALS
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.tests.conftest import open_listing

MakeReservation = Callable[..., Reservation]
LOOKUP = "store-pickup-lookup"


def client_for(user: Any, language: str = "en") -> APIClient:
    # force_authenticate skips sign-in only; the view and service checks still run.
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    client.credentials(HTTP_ACCEPT_LANGUAGE=language)
    return client


def lookup(client: APIClient, code: str) -> Any:
    return client.post(reverse(LOOKUP), {"code": code}, format="json")


def confirm(client: APIClient, reservation_id: Any) -> Any:
    url = reverse("store-pickup-confirm", kwargs={"id": reservation_id})
    return client.post(url, format="json")


def test_us44_lookup_returns_the_pickup_summary(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation(quantity=2)
    typed = (
        " " + reservation.pickup_code.lower()[:3] + " " + reservation.pickup_code[3:]
    )

    response = lookup(client_for(pickup_case.staff), typed)

    assert response.status_code == 200
    body = response.json()
    assert parse_datetime(body.pop("pickup_start")) == pickup_case.listing.pickup_start
    assert parse_datetime(body.pop("pickup_end")) == pickup_case.listing.pickup_end
    assert body == {
        "id": str(reservation.pk),
        "status": "reserved",
        "holder": "Fatou D.",
        "alternate": "Paul T.",
        "title": "Pain de la veille",
        "unit": "item",
        "quantity": 2,
        "pickup_code": reservation.pickup_code,
        "picked_up_at": None,
    }


def test_us44_confirm_marks_picked_up(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation()

    response = confirm(client_for(pickup_case.manager), reservation.pk)

    reservation.refresh_from_db()
    assert response.status_code == 200
    assert response.json()["status"] == "picked_up"
    assert response.json()["picked_up_at"].endswith("Z")
    assert reservation.status == ReservationStatus.PICKED_UP
    assert reservation.confirmed_by_id == pickup_case.manager.pk


def test_us44_second_confirm_says_already_picked_up_with_the_first_time(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation()
    client = client_for(pickup_case.staff)
    first = confirm(client, reservation.pk).json()

    response = confirm(client, reservation.pk)

    assert response.status_code == 409
    assert response.json()["code"] == "already_picked_up"
    assert response.json()["picked_up_at"] == first["picked_up_at"]
    assert response.json()["fields"] == {}


@pytest.mark.parametrize(
    "role", [User.Role.BENEFICIARY, User.Role.INTAKE_WORKER, User.Role.ADMIN]
)
def test_us44_other_roles_are_refused(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation, role: str
) -> None:
    # rule: BR-RES-001
    reservation = make_reservation()
    client = client_for(UserFactory(role=role))

    looked_up = lookup(client, reservation.pickup_code)
    confirmed = confirm(client, reservation.pk)

    reservation.refresh_from_db()
    assert looked_up.status_code == confirmed.status_code == 403
    assert looked_up.json()["code"] == "permission_denied"
    assert "Fatou" not in looked_up.content.decode()
    assert reservation.status == ReservationStatus.RESERVED


def test_us44_signed_out_is_refused(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation()
    client = client_for(None)
    assert lookup(client, reservation.pickup_code).status_code == 403
    assert confirm(client, reservation.pk).status_code == 403
    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.RESERVED


@pytest.mark.parametrize("role", [User.Role.STORE_STAFF, User.Role.STORE_MANAGER])
def test_us44_staff_of_another_store_cannot_see_or_confirm(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation, role: str
) -> None:
    # rule: BR-RES-001
    reservation = make_reservation()
    client = client_for(UserFactory(role=role, store=pickup_case.other_store))

    looked_up = lookup(client, reservation.pickup_code)
    confirmed = confirm(client, reservation.pk)

    reservation.refresh_from_db()
    assert (looked_up.status_code, looked_up.json()["code"]) == (409, "wrong_store")
    assert (confirmed.status_code, confirmed.json()["code"]) == (
        404,
        "unknown_reservation",
    )
    assert "Fatou" not in looked_up.content.decode() + confirmed.content.decode()
    assert reservation.status == ReservationStatus.RESERVED


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (ReservationStatus.CANCELLED, "cancelled"),
        (ReservationStatus.CANCELLED_BY_STORE, "cancelled"),
        (ReservationStatus.NO_SHOW, "no_show"),
    ],
)
def test_us44_finished_reservations_get_a_clear_refusal(
    pickup_case: SimpleNamespace,
    make_reservation: MakeReservation,
    status: str,
    code: str,
) -> None:
    reservation = make_reservation(status=status)
    client = client_for(pickup_case.staff)
    for response in (
        lookup(client, reservation.pickup_code),
        confirm(client, reservation.pk),
    ):
        assert response.status_code == 409
        assert response.json()["code"] == code
        assert response.json()["message"]


def test_us44_unknown_code_and_reservation_are_404(
    pickup_case: SimpleNamespace,
) -> None:
    client = client_for(pickup_case.staff)
    unknown_code = lookup(client, "ZZZZZZ")
    unknown_id = confirm(client, uuid4())
    assert (unknown_code.status_code, unknown_code.json()["code"]) == (
        404,
        "unknown_code",
    )
    assert (unknown_id.status_code, unknown_id.json()["code"]) == (
        404,
        "unknown_reservation",
    )
    assert "ZZZZZZ" not in unknown_code.json()["message"]


def test_us44_window_refusals_are_409(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    later = open_listing(
        pickup_case.store,
        pickup_start=pickup_case.now + timedelta(hours=1),
        pickup_end=pickup_case.now + timedelta(hours=2),
    )
    reservation = make_reservation(listing=later)
    response = confirm(client_for(pickup_case.staff), reservation.pk)
    assert (response.status_code, response.json()["code"]) == (409, "not_open_yet")


@pytest.mark.parametrize("code", ["", "ABC12", "ABC2345", "ABC-23", "ÀBC234"])
def test_us44_malformed_codes_are_validation_errors(
    pickup_case: SimpleNamespace, code: str
) -> None:
    response = lookup(client_for(pickup_case.staff), code)
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert list(response.json()["fields"]) == ["code"]


def test_us44_missing_code_is_a_validation_error(pickup_case: SimpleNamespace) -> None:
    response = client_for(pickup_case.staff).post(reverse(LOOKUP), {}, format="json")
    assert response.status_code == 400
    assert list(response.json()["fields"]) == ["code"]


def test_us44_refusals_are_translated_to_french(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    elsewhere = make_reservation(listing=pickup_case.other_listing)
    response = lookup(client_for(pickup_case.staff, "fr"), elsewhere.pickup_code)
    assert response.json()["message"].startswith(
        "Cette réservation se récupère ailleurs."
    )


@pytest.mark.parametrize("code", sorted(REFUSALS))
def test_us44_every_refusal_message_has_a_french_translation(code: str) -> None:
    message = REFUSALS[code][1]
    with translation.override("en"):
        english = str(message)
    with translation.override("fr"):
        assert str(message) != english


def test_us44_session_requests_need_csrf(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation()
    client = Client(enforce_csrf_checks=True)
    client.force_login(pickup_case.staff)
    response = client.post(
        reverse("store-pickup-confirm", kwargs={"id": reservation.pk}),
        HTTP_ACCEPT_LANGUAGE="en",
    )
    reservation.refresh_from_db()
    assert response.status_code == 403
    assert "CSRF" in response.json()["message"]
    assert reservation.status == ReservationStatus.RESERVED
