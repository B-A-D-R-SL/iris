# AI contribution: 50% or more AI-generated
"""Admin store API (US-14, T-02.14.2).

The services have their own tests (test_store_admin_service.py); these check
access for every role, the HTTP contract and one full path to the database.
"""

from datetime import timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.households.tests.factories import HouseholdFactory
from modules.listings.models import ListingStatus
from modules.listings.tests.factories import ListingFactory
from modules.notifications.models import EmailLog
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.tests.factories import ReservationFactory
from modules.stores.models import Store
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


def _store(**values: Any) -> Store:
    return cast(Store, StoreFactory(**values))


def _reservation(**values: Any) -> Reservation:
    return cast(Reservation, ReservationFactory(**values))


LIST_URL = "/api/staff/stores/"
NON_ADMIN_ROLES = [
    User.Role.BENEFICIARY,
    User.Role.STORE_STAFF,
    User.Role.STORE_MANAGER,
    User.Role.INTAKE_WORKER,
]
WEEK = {
    "mon": {"open": "08:00", "close": "20:00"},
    "tue": {"open": "08:00", "close": "20:00"},
    "wed": {"open": "08:00", "close": "20:00"},
    "thu": {"open": "08:00", "close": "21:00"},
    "fri": {"open": "08:00", "close": "21:00"},
    "sat": {"open": "09:00", "close": "18:00"},
    "sun": None,
}


def detail_url(store_id: object) -> str:
    return f"{LIST_URL}{store_id}/"


def deactivate_url(store_id: object) -> str:
    return f"{LIST_URL}{store_id}/deactivate/"


def reactivate_url(store_id: object) -> str:
    return f"{LIST_URL}{store_id}/reactivate/"


@pytest.fixture
def admin() -> User:
    return cast(User, UserFactory(role=User.Role.ADMIN))


@pytest.fixture
def admin_client(admin: User) -> APIClient:
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_login(admin)
    return client


def _signed_in(role: str) -> APIClient:
    store = (
        _store() if role in (User.Role.STORE_STAFF, User.Role.STORE_MANAGER) else None
    )
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_login(UserFactory(role=role, store=store))
    return client


def _every_endpoint(client: APIClient, store: Store) -> list[Any]:
    return [
        client.get(LIST_URL),
        client.get(detail_url(store.pk)),
        client.patch(detail_url(store.pk), {"city": "Laval"}, format="json"),
        client.post(deactivate_url(store.pk), {"reason": "Closed"}, format="json"),
        client.post(reactivate_url(store.pk), {"reason": "Open"}, format="json"),
    ]


def _open_listing(store: Store, **kwargs: Any) -> Any:
    start = timezone.now() + timedelta(hours=2)
    return ListingFactory(
        store=store, pickup_start=start, pickup_end=start + timedelta(hours=2), **kwargs
    )


# --- access -------------------------------------------------------------------


def test_signed_out_requests_get_401() -> None:
    store = _store()
    for response in _every_endpoint(APIClient(), store):
        assert response.status_code == 401


# rule: BR-STORE-001
@pytest.mark.parametrize("role", NON_ADMIN_ROLES)
def test_non_admins_get_403_and_nothing_changes(role: str) -> None:
    store = _store(city="Montréal")

    for response in _every_endpoint(_signed_in(role), store):
        assert response.status_code == 403
        assert response.json()["message"] == "Only admins can manage stores."

    store.refresh_from_db()
    assert store.city == "Montréal" and store.is_active is True
    assert not AuditEvent.objects.filter(target_type="store").exists()


def test_inactive_admin_gets_403() -> None:
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_login(UserFactory(role=User.Role.ADMIN, is_active=False))
    for response in _every_endpoint(client, _store()):
        assert response.status_code in (401, 403)


def test_unknown_store_is_404(admin_client: APIClient) -> None:
    missing = uuid4()
    responses = [
        admin_client.get(detail_url(missing)),
        admin_client.patch(detail_url(missing), {"city": "Laval"}, format="json"),
        admin_client.post(deactivate_url(missing), {"reason": "x"}, format="json"),
        admin_client.post(reactivate_url(missing), {"reason": "x"}, format="json"),
    ]
    for response in responses:
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


# --- list and detail ----------------------------------------------------------


def test_list_searches_filters_and_counts(admin_client: APIClient) -> None:
    cafe = _store(name="Café Démo", street_name="rue Ontario E")
    _store(name="Boulangerie Exemple", is_active=False, street_name="av. du Parc")
    _open_listing(cafe)

    body = admin_client.get(LIST_URL, {"q": "ontario"}).json()

    assert body["count"] == 1
    assert body["counts"] == {"all": 1, "active": 1, "inactive": 0}
    [row] = body["results"]
    assert row["name"] == "Café Démo"
    assert row["open_listings"] == 1
    assert row["is_active"] is True

    inactive = admin_client.get(LIST_URL, {"status": "inactive"}).json()
    assert [r["name"] for r in inactive["results"]] == ["Boulangerie Exemple"]
    assert inactive["counts"] == {"all": 2, "active": 1, "inactive": 1}


def test_list_refuses_an_unknown_status(admin_client: APIClient) -> None:
    response = admin_client.get(LIST_URL, {"status": "closed"})
    assert response.status_code == 400
    assert "status" in response.json()["fields"]


def test_detail_includes_the_deactivation_preview(admin_client: APIClient) -> None:
    store = _store(opening_hours={"notes": "Lun-ven 8h-20h"})
    listing = _open_listing(store)
    _reservation(listing=listing, household=HouseholdFactory(email="a@example.test"))
    _reservation(listing=listing, household=HouseholdFactory(email="b@example.test"))
    _reservation(listing=listing, household=HouseholdFactory(email=None))

    body = admin_client.get(detail_url(store.pk)).json()

    assert body["open_listings"] == 1
    assert body["households_to_notify"] == 2
    assert body["opening_hours"]["notes"] == "Lun-ven 8h-20h"
    assert body["opening_hours"]["mon"] is None
    assert body["is_badr"] is False


# --- edit ---------------------------------------------------------------------


# rule: BR-STORE-001
def test_patch_saves_and_audits(admin_client: APIClient, admin: User) -> None:
    store = _store()

    response = admin_client.patch(
        detail_url(store.pk),
        {"phone": "+15145550110", "opening_hours": WEEK, "unit": ""},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["opening_hours"]["sun"] is None
    store.refresh_from_db()
    assert store.phone == "+15145550110" and store.opening_hours == WEEK
    event = AuditEvent.objects.get(action="update", target_type="store")
    assert event.metadata == {"fields": "opening_hours,phone"}
    assert event.actor == admin


# rule: BR-STORE-001
@pytest.mark.parametrize("field", ["is_active", "is_badr", "application", "id"])
def test_patch_refuses_protected_fields(admin_client: APIClient, field: str) -> None:
    store = _store()

    response = admin_client.patch(detail_url(store.pk), {field: False}, format="json")

    assert response.status_code == 400
    assert response.json()["fields"][field] == ["This field cannot be changed."]


def test_patch_returns_field_errors(admin_client: APIClient) -> None:
    response = admin_client.patch(
        detail_url(_store().pk),
        {
            "postal_code": "12345",
            "opening_hours": WEEK | {"mon": {"open": "20:00", "close": "08:00"}},
        },
        format="json",
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert "opening_hours" in body["fields"]


def test_patch_messages_follow_the_language(admin_client: APIClient) -> None:
    response = admin_client.patch(
        detail_url(_store().pk),
        {"is_badr": True},
        format="json",
        HTTP_ACCEPT_LANGUAGE="fr",
    )
    assert response.json()["fields"]["is_badr"] == [
        "Ce champ ne peut pas être modifié."
    ]


# --- deactivate and reactivate ------------------------------------------------


# rule: BR-STORE-004
def test_badr_store_deactivation_is_400(admin_client: APIClient) -> None:
    store = _store(is_badr=True)

    response = admin_client.post(
        deactivate_url(store.pk), {"reason": "x"}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["code"] == "store_is_badr"


# rule: BR-STORE-004
def test_repeated_status_changes_are_409(admin_client: APIClient) -> None:
    inactive, active = _store(is_active=False), _store()

    first = admin_client.post(
        deactivate_url(inactive.pk), {"reason": "x"}, format="json"
    )
    second = admin_client.post(
        reactivate_url(active.pk), {"reason": "x"}, format="json"
    )

    assert (first.status_code, first.json()["code"]) == (409, "store_already_inactive")
    assert (second.status_code, second.json()["code"]) == (409, "store_already_active")


# rule: BR-STORE-005
@pytest.mark.parametrize("body", [{}, {"reason": "  "}, {"reason": "x" * 501}])
def test_status_changes_need_a_reason(admin_client: APIClient, body: dict) -> None:
    store = _store()

    response = admin_client.post(deactivate_url(store.pk), body, format="json")

    assert response.status_code == 400
    assert "reason" in response.json()["fields"]
    store.refresh_from_db()
    assert store.is_active is True


# rule: BR-STORE-001
# rule: BR-STORE-002
# rule: BR-STORE-003
def test_edit_deactivate_reactivate_through_the_database(
    admin_client: APIClient, notification_rules: Any
) -> None:
    """Integration: API to database for the whole admin path (AC1 to AC3)."""
    store = _store(name="Épicerie Démo")
    listing = _open_listing(store, title="Bread bundle", quantity_reserved=3)
    household = HouseholdFactory(email="family@example.test", preferred_language="fr")
    reservation = _reservation(listing=listing, household=household, quantity=3)

    edited = admin_client.patch(detail_url(store.pk), {"city": "Laval"}, format="json")
    deactivated = admin_client.post(
        deactivate_url(store.pk), {"reason": "Closed for renovations"}, format="json"
    )
    reactivated = admin_client.post(
        reactivate_url(store.pk), {"reason": "Renovations finished"}, format="json"
    )

    assert (
        edited.status_code == deactivated.status_code == reactivated.status_code == 200
    )
    assert deactivated.json()["is_active"] is False
    assert deactivated.json()["listings_cancelled"] == 1
    assert deactivated.json()["reservations_cancelled"] == 1
    assert reactivated.json()["is_active"] is True
    store.refresh_from_db()
    listing.refresh_from_db()
    reservation.refresh_from_db()
    assert store.city == "Laval" and store.is_active is True
    assert listing.status == ListingStatus.CANCELLED
    assert reservation.status == ReservationStatus.CANCELLED_BY_STORE
    assert reservation.late_cancel is False
    assert (
        EmailLog.objects.filter(
            template_key="reservation_cancelled_by_store", language="fr"
        ).count()
        == 1
    )
    assert list(
        AuditEvent.objects.filter(target_type="store", target_id=str(store.pk))
        .order_by("created_at", "id")
        .values_list("action", flat=True)
    ) == ["update", "deactivate", "reactivate"]


def test_schema_documents_the_store_endpoints(admin_client: APIClient) -> None:
    schema = admin_client.get("/api/schema/").content.decode()
    for operation in (
        "staff_stores_list",
        "staff_stores_retrieve",
        "staff_stores_partial_update",
        "staff_stores_deactivate",
        "staff_stores_reactivate",
    ):
        assert operation in schema


# rule: BR-STORE-004
def test_detail_says_whether_the_status_can_change(admin_client: APIClient) -> None:
    """The screen shows the status switch from the API, not from is_badr."""
    badr, partner = _store(is_badr=True), _store()

    assert admin_client.get(detail_url(badr.pk)).json()["can_change_status"] is False
    assert admin_client.get(detail_url(partner.pk)).json()["can_change_status"] is True
