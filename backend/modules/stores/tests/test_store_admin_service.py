# AI contribution: 50% or more AI-generated
"""Store administration services (US-14): edit, deactivate, reactivate."""

from datetime import timedelta
from typing import Any, cast

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.households.tests.factories import HouseholdFactory
from modules.listings.models import ListingStatus
from modules.listings.tests.factories import ListingFactory
from modules.notifications.models import EmailLog
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.tests.factories import ReservationFactory
from modules.stores import queries, services
from modules.stores.models import Store
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


def _store(**values: Any) -> Store:
    return cast(Store, StoreFactory(**values))


def _reservation(**values: Any) -> Reservation:
    return cast(Reservation, ReservationFactory(**values))


WEEK = {
    "mon": {"open": "08:00", "close": "20:00"},
    "tue": {"open": "08:00", "close": "20:00"},
    "wed": {"open": "08:00", "close": "20:00"},
    "thu": {"open": "08:00", "close": "21:00"},
    "fri": {"open": "08:00", "close": "21:00"},
    "sat": {"open": "09:00", "close": "18:00"},
    "sun": None,
}


def _events(action: str) -> list[AuditEvent]:
    return list(AuditEvent.objects.filter(action=action, target_type="store"))


def _open_listing(store: Store, **kwargs: Any) -> Any:
    start = timezone.now() + timedelta(hours=2)
    return ListingFactory(
        store=store, pickup_start=start, pickup_end=start + timedelta(hours=2), **kwargs
    )


def _ended_listing(store: Store) -> Any:
    start = timezone.now() - timedelta(hours=5)
    return ListingFactory(
        store=store, pickup_start=start, pickup_end=start + timedelta(hours=2)
    )


# --- update_store -------------------------------------------------------------


# rule: BR-STORE-001
def test_admin_edits_every_editable_field_and_audits_the_names(admin) -> None:
    store = _store(opening_hours={})
    changes = {
        "name": "Épicerie Démo du Quartier",
        "street_number": "1234",
        "street_name": "rue Saint-Denis",
        "unit": "B",
        "city": "Laval",
        "postal_code": "h2x3k2",
        "phone": "+15145550110",
        "email": "bonjour@epicerie-demo.example",
        "opening_hours": WEEK,
        "pickup_instructions": "Back door, ring the bell",
    }

    updated = services.update_store(store.pk, changes, admin)

    store.refresh_from_db()
    assert updated.pk == store.pk
    assert store.postal_code == "H2X 3K2"
    assert store.opening_hours == WEEK
    for field in set(changes) - {"postal_code"}:
        assert getattr(store, field) == changes[field]
    [event] = _events("update")
    assert event.metadata == {"fields": ",".join(sorted(changes))}
    assert event.actor == admin


def test_only_changed_fields_are_audited(admin) -> None:
    store = _store(city="Montréal", phone="+15145550100")

    services.update_store(
        store.pk, {"city": "Montréal", "phone": "+15145550199"}, admin
    )

    [event] = _events("update")
    assert event.metadata == {"fields": "phone"}


def test_no_change_records_nothing(admin) -> None:
    store = _store(postal_code="H2X 1Y4")

    services.update_store(
        store.pk, {"postal_code": "h2x1y4", "name": store.name}, admin
    )

    assert _events("update") == []


def test_blank_optional_text_is_stored_as_empty(admin) -> None:
    store = _store(unit="B", pickup_instructions="Side door")

    services.update_store(store.pk, {"unit": "  ", "pickup_instructions": ""}, admin)

    store.refresh_from_db()
    assert store.unit is None and store.pickup_instructions is None


@pytest.mark.parametrize(
    "field", ["is_badr", "is_active", "application", "id", "created_at", "updated_at"]
)
def test_protected_fields_cannot_be_edited(admin, field) -> None:
    store = _store()

    with pytest.raises(ValidationError) as error:
        services.update_store(store.pk, {field: True}, admin)

    assert field in error.value.message_dict
    assert _events("update") == []


def test_free_text_hours_notes_are_kept(admin) -> None:
    store = _store(opening_hours={"notes": "Lun-ven 8h-20h"})

    services.update_store(store.pk, {"opening_hours": WEEK}, admin)

    store.refresh_from_db()
    assert store.opening_hours == WEEK | {"notes": "Lun-ven 8h-20h"}


@pytest.mark.parametrize(
    "hours",
    [
        {"mon": {"open": "08:00", "close": "20:00"}},
        WEEK | {"mon": {"open": "20:00", "close": "08:00"}},
        {day: None for day in WEEK},
    ],
)
def test_invalid_hours_are_refused(admin, hours) -> None:
    store = _store()

    with pytest.raises(ValidationError) as error:
        services.update_store(store.pk, {"opening_hours": hours}, admin)

    assert "opening_hours" in error.value.message_dict


@pytest.mark.parametrize(
    "changes",
    [{"name": "A"}, {"postal_code": "12345"}, {"phone": "514-555"}, {"email": "nope"}],
)
def test_model_rules_still_apply(admin, changes) -> None:
    with pytest.raises(ValidationError):
        services.update_store(_store().pk, changes, admin)
    assert _events("update") == []


@pytest.mark.parametrize("role", ["intake_worker", "beneficiary"])
def test_only_active_admins_edit(role) -> None:
    with pytest.raises(PermissionDenied):
        services.update_store(_store().pk, {"city": "Laval"}, UserFactory(role=role))


def test_inactive_admin_cannot_edit() -> None:
    admin = UserFactory(role=User.Role.ADMIN, is_active=False)
    with pytest.raises(PermissionDenied):
        services.update_store(_store().pk, {"city": "Laval"}, admin)


def test_unknown_store_is_not_found(admin) -> None:
    store = _store()
    store_id = store.pk
    store.delete()
    with pytest.raises(Store.DoesNotExist):
        services.update_store(store_id, {"city": "Laval"}, admin)


# --- deactivate_store ---------------------------------------------------------


# rule: BR-STORE-002
# rule: BR-STORE-003
def test_deactivation_cancels_open_listings_and_their_reservations(
    admin, notification_rules
) -> None:
    store = _store(name="Épicerie Démo")
    listing = _open_listing(store, title="Bread bundle", quantity_reserved=3)
    ended = _ended_listing(store)
    household = HouseholdFactory(email="family@example.test", preferred_language="en")
    open_claim = _reservation(listing=listing, household=household, quantity=3)
    missed = _reservation(listing=ended)

    result = services.deactivate_store(store.pk, admin, "  Closed for renovations ")

    assert (result.listings_cancelled, result.reservations_cancelled) == (1, 1)
    store.refresh_from_db()
    listing.refresh_from_db()
    ended.refresh_from_db()
    open_claim.refresh_from_db()
    missed.refresh_from_db()
    assert store.is_active is False
    assert listing.status == ListingStatus.CANCELLED
    assert ended.status == ListingStatus.PUBLISHED  # left for US-45 no-shows
    assert open_claim.status == ReservationStatus.CANCELLED_BY_STORE
    assert open_claim.late_cancel is False
    assert missed.status == ReservationStatus.RESERVED
    [email] = EmailLog.objects.filter(template_key="reservation_cancelled_by_store")
    assert email.language == "en"
    [event] = _events("deactivate")
    assert event.metadata == {
        "reason": "Closed for renovations",
        "listings_cancelled": 1,
        "reservations_cancelled": 1,
    }


def test_preview_matches_what_deactivation_cancels(admin) -> None:
    store = _store()
    listing = _open_listing(store)
    household = HouseholdFactory(email="family@example.test")
    _reservation(listing=listing, household=household)
    _reservation(listing=_open_listing(store), household=household)
    _reservation(listing=listing, household=HouseholdFactory(email=None))
    _reservation(
        listing=_ended_listing(store),
        household=HouseholdFactory(email="ended@example.test"),
    )

    preview = queries.deactivation_preview(store.pk, timezone.now())

    assert preview == {"open_listings": 2, "households_to_notify": 1}


# rule: BR-STORE-004
def test_badr_store_cannot_be_deactivated(admin) -> None:
    store = _store(is_badr=True)

    with pytest.raises(services.StoreIsBadr):
        services.deactivate_store(store.pk, admin, "Closed")

    store.refresh_from_db()
    assert store.is_active is True
    assert _events("deactivate") == []


def test_deactivating_twice_is_refused(admin) -> None:
    store = _store(is_active=False)

    with pytest.raises(services.StoreStatusUnchanged) as error:
        services.deactivate_store(store.pk, admin, "Closed")

    assert error.value.is_active is False


# rule: BR-STORE-005
@pytest.mark.parametrize(
    "reason",
    ["", "   ", "x" * 501, "Manager SIN 123 456 789", "Gérant résident permanent"],
)
def test_deactivation_needs_a_valid_reason(admin, reason) -> None:
    store = _store()
    listing = _open_listing(store)

    with pytest.raises(ValidationError) as error:
        services.deactivate_store(store.pk, admin, reason)

    assert "reason" in error.value.message_dict
    store.refresh_from_db()
    listing.refresh_from_db()
    assert store.is_active is True
    assert listing.status == ListingStatus.PUBLISHED


def test_only_admins_deactivate() -> None:
    with pytest.raises(PermissionDenied):
        services.deactivate_store(
            _store().pk, UserFactory(role="intake_worker"), "Closed"
        )


# --- reactivate_store ---------------------------------------------------------


def test_reactivation_restores_posting_but_not_listings(admin) -> None:
    store = _store()
    listing = _open_listing(store)
    services.deactivate_store(store.pk, admin, "Closed for renovations")

    services.reactivate_store(store.pk, admin, "Renovations finished")

    store.refresh_from_db()
    listing.refresh_from_db()
    assert store.is_active is True
    assert listing.status == ListingStatus.CANCELLED
    [event] = _events("reactivate")
    assert event.metadata == {"reason": "Renovations finished"}


def test_reactivating_an_active_store_is_refused(admin) -> None:
    with pytest.raises(services.StoreStatusUnchanged) as error:
        services.reactivate_store(_store().pk, admin, "Open")
    assert error.value.is_active is True


# rule: BR-STORE-005
@pytest.mark.parametrize("reason", [" ", "Résidente permanente maintenant"])
def test_reactivation_needs_a_valid_reason(admin, reason) -> None:
    store = _store(is_active=False)
    with pytest.raises(ValidationError):
        services.reactivate_store(store.pk, admin, reason)
    store.refresh_from_db()
    assert store.is_active is False


# --- queries ------------------------------------------------------------------


def test_list_search_filter_and_counts() -> None:
    _store(name="Café Démo", street_number="88", street_name="rue Ontario E")
    _store(name="Boulangerie Exemple", is_active=False)
    _store(name="Marché Hochelaga", street_name="rue Ontario E")

    assert [s.name for s in queries.staff_stores("ontario")] == [
        "Café Démo",
        "Marché Hochelaga",
    ]
    assert [s.name for s in queries.staff_stores("88 rue")] == ["Café Démo"]
    assert [s.name for s in queries.staff_stores(status="inactive")] == [
        "Boulangerie Exemple"
    ]
    assert queries.status_counts() == {"all": 3, "active": 2, "inactive": 1}
    assert queries.status_counts("ontario") == {"all": 2, "active": 2, "inactive": 0}


# --- logging ------------------------------------------------------------------


def test_store_changes_are_logged_after_commit_without_personal_text(
    admin, partner_events, django_capture_on_commit_callbacks
) -> None:
    """Each change logs its event once it commits: ids and counts, no reason or name."""
    store = _store(name="Épicerie Secrète")
    _open_listing(store)

    with django_capture_on_commit_callbacks(execute=True):
        services.update_store(store.pk, {"city": "Laval"}, admin)
    with django_capture_on_commit_callbacks(execute=True):
        services.deactivate_store(store.pk, admin, "Fermé pour rénovations")
    with django_capture_on_commit_callbacks(execute=True):
        services.reactivate_store(store.pk, admin, "Rénovations terminées")

    events = [
        vars(record)
        for record in partner_events.records
        if getattr(record, "event", "").startswith("store_")
    ]
    assert [event["event"] for event in events] == [
        "store_updated",
        "store_deactivated",
        "store_reactivated",
    ]
    assert all(event["store_id"] == str(store.pk) for event in events)
    assert events[1]["listings_cancelled"] == 1
    assert events[1]["reservations_cancelled"] == 0
    logged = " ".join(str(event) for event in events)
    assert "rénovations" not in logged.lower()
    assert "Secrète" not in logged


def test_nothing_is_logged_when_the_change_rolls_back(
    admin, partner_events, django_capture_on_commit_callbacks
) -> None:
    store = _store()
    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(ValidationError),
    ):
        services.deactivate_store(store.pk, admin, "   ")
    assert not [r for r in partner_events.records if r.name == "iris.stores"]
