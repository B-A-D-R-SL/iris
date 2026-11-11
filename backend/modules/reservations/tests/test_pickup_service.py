# AI contribution: 50% or more AI-generated
"""US-44 lookup and confirmation against PostgreSQL (T-06.44.1)."""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection, transaction
from django.utils import timezone

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.reservations import queries, services
from modules.reservations.domain import pickup
from modules.reservations.domain.pickup import PickupRefused
from modules.reservations.models import Reservation, ReservationStatus
from modules.reservations.tests.conftest import open_listing, pickup_household

MakeReservation = Callable[..., Reservation]


def refusal(call: Callable[[], Any]) -> PickupRefused:
    with pytest.raises(PickupRefused) as caught:
        call()
    return caught.value


def test_us44_lookup_shows_who_and_what_without_contact_details(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-003
    reservation = make_reservation(quantity=3)

    found = queries.lookup_pickup(
        pickup_case.staff, reservation.pickup_code, now=pickup_case.now
    )

    assert found == queries.Pickup(
        id=reservation.pk,
        status=ReservationStatus.RESERVED,
        holder="Fatou D.",
        alternate="Paul T.",
        title="Pain de la veille",
        unit=pickup_case.listing.unit,
        quantity=3,
        pickup_code=reservation.pickup_code,
        pickup_start=pickup_case.listing.pickup_start,
        pickup_end=pickup_case.listing.pickup_end,
        picked_up_at=None,
    )
    reservation.refresh_from_db()
    assert reservation.status == ReservationStatus.RESERVED


def test_us44_manager_can_look_up_and_confirm(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation()
    code = reservation.pickup_code
    assert queries.lookup_pickup(pickup_case.manager, code, now=pickup_case.now)
    assert services.confirm_pickup(reservation.pk, pickup_case.manager).status == (
        ReservationStatus.PICKED_UP
    )


def test_us44_unknown_code_is_refused(pickup_case: SimpleNamespace) -> None:
    refused = refusal(
        lambda: queries.lookup_pickup(pickup_case.staff, "ZZZZZZ", now=pickup_case.now)
    )
    assert refused.code == pickup.UNKNOWN_CODE


def test_us44_code_of_another_store_says_wrong_store_only(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-001
    elsewhere = make_reservation(listing=pickup_case.other_listing)

    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, elsewhere.pickup_code, now=pickup_case.now
        )
    )

    assert (refused.code, refused.picked_up_at) == (pickup.WRONG_STORE, None)


def test_us44_finished_reservation_of_another_store_is_unknown(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-001
    elsewhere = make_reservation(
        listing=pickup_case.other_listing, status=ReservationStatus.CANCELLED
    )
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, elsewhere.pickup_code, now=pickup_case.now
        )
    )
    assert refused.code == pickup.UNKNOWN_CODE


def test_us44_two_live_reservations_with_one_code_are_refused(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-004
    first = make_reservation()
    make_reservation(
        listing=open_listing(pickup_case.store),
        household=pickup_household(),
        pickup_code=first.pickup_code,
    )
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, first.pickup_code, now=pickup_case.now
        )
    )
    assert refused.code == pickup.AMBIGUOUS_CODE


def test_us44_live_reservation_wins_over_a_finished_one_with_the_same_code(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-004
    live = make_reservation()
    make_reservation(
        listing=open_listing(pickup_case.store),
        pickup_code=live.pickup_code,
        status=ReservationStatus.PICKED_UP,
        picked_up_at=pickup_case.now - timedelta(days=1),
    )
    found = queries.lookup_pickup(
        pickup_case.staff, live.pickup_code, now=pickup_case.now
    )
    assert found.id == live.pk


def test_us44_finished_local_does_not_hide_live_elsewhere(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-001; BR-RES-004
    finished = make_reservation(
        status=ReservationStatus.PICKED_UP,
        picked_up_at=pickup_case.now - timedelta(days=1),
    )
    make_reservation(
        listing=pickup_case.other_listing,
        household=pickup_household(),
        pickup_code=finished.pickup_code,
    )
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, finished.pickup_code, now=pickup_case.now
        )
    )
    assert refused.code == pickup.WRONG_STORE


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (ReservationStatus.CANCELLED, pickup.CANCELLED),
        (ReservationStatus.CANCELLED_BY_STORE, pickup.CANCELLED),
        (ReservationStatus.NO_SHOW, pickup.NO_SHOW),
    ],
)
def test_us44_finished_reservation_is_refused_with_its_reason(
    pickup_case: SimpleNamespace,
    make_reservation: MakeReservation,
    status: str,
    code: str,
) -> None:
    # rule: BR-RES-002
    reservation = make_reservation(status=status)
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, reservation.pickup_code, now=pickup_case.now
        )
    )
    assert refused.code == code


def test_us44_already_picked_up_reports_the_first_time(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    first_time = pickup_case.now - timedelta(minutes=10)
    reservation = make_reservation(
        status=ReservationStatus.PICKED_UP, picked_up_at=first_time
    )
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, reservation.pickup_code, now=pickup_case.now
        )
    )
    assert (refused.code, refused.picked_up_at) == (
        pickup.ALREADY_PICKED_UP,
        first_time,
    )


@pytest.mark.parametrize(
    ("start_offset", "end_offset", "code"),
    [
        (timedelta(minutes=5), timedelta(hours=2), pickup.NOT_OPEN_YET),
        (-timedelta(hours=3), -timedelta(minutes=1), pickup.WINDOW_ENDED),
    ],
)
def test_us44_lookup_outside_the_window_is_refused(
    pickup_case: SimpleNamespace,
    make_reservation: MakeReservation,
    start_offset: timedelta,
    end_offset: timedelta,
    code: str,
) -> None:
    # rule: BR-RES-002
    listing = open_listing(
        pickup_case.store,
        pickup_start=pickup_case.now + start_offset,
        pickup_end=pickup_case.now + end_offset,
    )
    reservation = make_reservation(listing=listing)
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, reservation.pickup_code, now=pickup_case.now
        )
    )
    assert refused.code == code


def test_us44_anonymized_household_is_treated_as_unknown(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    household = pickup_household()
    household.anonymized_at = pickup_case.now
    household.save(update_fields=["anonymized_at"])
    reservation = make_reservation(household=household)
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, reservation.pickup_code, now=pickup_case.now
        )
    )
    assert refused.code == pickup.UNKNOWN_CODE


def test_us44_anonymized_other_store_live_is_unknown(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-003
    household = pickup_household()
    household.anonymized_at = pickup_case.now
    household.save(update_fields=["anonymized_at"])
    elsewhere = make_reservation(listing=pickup_case.other_listing, household=household)
    refused = refusal(
        lambda: queries.lookup_pickup(
            pickup_case.staff, elsewhere.pickup_code, now=pickup_case.now
        )
    )
    assert refused.code == pickup.UNKNOWN_CODE


def test_us44_confirm_records_who_and_when_once_and_keeps_stock(
    pickup_case: SimpleNamespace,
    make_reservation: MakeReservation,
    caplog: pytest.LogCaptureFixture,
    django_capture_on_commit_callbacks: Any,
) -> None:
    # rule: BR-RES-005
    listing = pickup_case.listing
    listing.quantity_reserved = 2
    listing.save(update_fields=["quantity_reserved"])
    reservation = make_reservation()

    # Exercise the configured logger without enabling INFO just for this test.
    assert services.logger.isEnabledFor(logging.INFO)
    with django_capture_on_commit_callbacks(execute=True):
        confirmed = services.confirm_pickup(reservation.pk, pickup_case.staff)

    reservation.refresh_from_db()
    listing.refresh_from_db()
    assert reservation.status == confirmed.status == ReservationStatus.PICKED_UP
    assert reservation.picked_up_at == confirmed.picked_up_at == timezone.now()
    assert reservation.confirmed_by_id == pickup_case.staff.pk
    assert (confirmed.holder, confirmed.alternate) == ("Fatou D.", "Paul T.")
    assert (listing.quantity_total, listing.quantity_reserved) == (10, 2)
    assert [record.getMessage() for record in caplog.records] == ["pickup_confirmed"]
    assert "Fatou" not in caplog.text
    assert reservation.pickup_code not in caplog.text


def test_us44_second_confirmation_is_refused_and_keeps_the_first(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation()
    services.confirm_pickup(reservation.pk, pickup_case.staff)

    later = pickup_case.now + timedelta(minutes=5)
    refused = refusal(
        lambda: services.confirm_pickup(reservation.pk, pickup_case.manager, now=later)
    )

    reservation.refresh_from_db()
    assert (refused.code, refused.picked_up_at) == (
        pickup.ALREADY_PICKED_UP,
        pickup_case.now,
    )
    assert reservation.picked_up_at == pickup_case.now
    assert reservation.confirmed_by_id == pickup_case.staff.pk


@pytest.mark.django_db(transaction=True)
def test_us44_simultaneous_confirmations_record_one_pickup(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    reservation = make_reservation()

    def confirm(_: int) -> str:
        close_old_connections()
        try:
            services.confirm_pickup(reservation.pk, pickup_case.staff)
            return "confirmed"
        except PickupRefused as refused:
            return refused.code
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=6) as workers:
        results = list(workers.map(confirm, range(6)))

    assert results.count("confirmed") == 1
    assert results.count(pickup.ALREADY_PICKED_UP) == 5


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("window_ended", [False, True])
def test_us44_confirmation_uses_time_after_acquiring_the_lock(
    pickup_case: SimpleNamespace,
    make_reservation: MakeReservation,
    monkeypatch: pytest.MonkeyPatch,
    window_ended: bool,
) -> None:
    # rule: BR-RES-002. Advance the clock while another transaction holds the row.
    reservation = make_reservation()
    lock_requested = Event()
    clock = [pickup_case.now]
    later = (
        pickup_case.listing.pickup_end + timedelta(seconds=1)
        if window_ended
        else pickup_case.now + timedelta(minutes=5)
    )
    monkeypatch.setattr(timezone, "now", lambda: clock[0])

    def observe_lock(
        execute: Callable[..., Any],
        sql: str,
        params: Any,
        many: bool,
        context: Any,
    ) -> Any:
        if "FOR UPDATE" in sql:
            lock_requested.set()
        return execute(sql, params, many, context)

    def confirm() -> str:
        close_old_connections()
        try:
            with connection.execute_wrapper(observe_lock):
                services.confirm_pickup(reservation.pk, pickup_case.staff)
            return "confirmed"
        except PickupRefused as refused:
            return refused.code
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=1) as worker:
        with transaction.atomic():
            Reservation.objects.select_for_update().get(pk=reservation.pk)
            result = worker.submit(confirm)
            assert lock_requested.wait(timeout=10), (
                "Confirmation never requested its lock"
            )
            clock[0] = later
        outcome = result.result(timeout=10)

    reservation.refresh_from_db()
    if window_ended:
        assert outcome == pickup.WINDOW_ENDED
        assert reservation.status == ReservationStatus.RESERVED
        assert reservation.picked_up_at is None
        assert reservation.confirmed_by_id is None
    else:
        assert outcome == "confirmed"
        assert reservation.status == ReservationStatus.PICKED_UP
        assert reservation.picked_up_at == later
        assert reservation.confirmed_by_id == pickup_case.staff.pk


def test_us44_staff_of_another_store_cannot_confirm(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-001
    reservation = make_reservation()
    refused = refusal(
        lambda: services.confirm_pickup(reservation.pk, pickup_case.other_staff)
    )
    reservation.refresh_from_db()
    assert refused.code == pickup.UNKNOWN_RESERVATION
    assert reservation.status == ReservationStatus.RESERVED
    assert reservation.confirmed_by_id is None


@pytest.mark.parametrize(
    "status",
    [
        ReservationStatus.CANCELLED,
        ReservationStatus.CANCELLED_BY_STORE,
        ReservationStatus.NO_SHOW,
    ],
)
def test_us44_finished_reservation_cannot_be_confirmed(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation, status: str
) -> None:
    # rule: BR-RES-002
    reservation = make_reservation(status=status)
    refusal(lambda: services.confirm_pickup(reservation.pk, pickup_case.staff))
    reservation.refresh_from_db()
    assert (reservation.status, reservation.picked_up_at) == (status, None)


def test_us44_confirm_rechecks_the_window(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-002
    reservation = make_reservation()
    after_end = pickup_case.listing.pickup_end + timedelta(seconds=1)
    refused = refusal(
        lambda: services.confirm_pickup(
            reservation.pk, pickup_case.staff, now=after_end
        )
    )
    reservation.refresh_from_db()
    assert refused.code == pickup.WINDOW_ENDED
    assert reservation.status == ReservationStatus.RESERVED


@pytest.mark.parametrize(
    "role", [User.Role.BENEFICIARY, User.Role.INTAKE_WORKER, User.Role.ADMIN]
)
def test_us44_accounts_without_a_store_role_are_denied(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation, role: str
) -> None:
    # rule: BR-RES-001
    user = UserFactory(role=role)
    reservation = make_reservation()
    with pytest.raises(PermissionDenied):
        queries.lookup_pickup(user, reservation.pickup_code, now=pickup_case.now)
    with pytest.raises(PermissionDenied):
        services.confirm_pickup(reservation.pk, user)


def test_us44_inactive_staff_are_denied(
    pickup_case: SimpleNamespace, make_reservation: MakeReservation
) -> None:
    # rule: BR-RES-001
    staff = UserFactory(
        role=User.Role.STORE_STAFF, store=pickup_case.store, is_active=False
    )
    reservation = make_reservation()
    with pytest.raises(PermissionDenied):
        services.confirm_pickup(reservation.pk, staff)
