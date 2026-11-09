# AI contribution: 50% or more AI-generated
"""reserve() (US-41, #516): every acceptance criterion and every refusal."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from django.utils import timezone

from modules.reservations import services
from modules.reservations.domain.codes import PICKUP_CODE_ALPHABET
from modules.reservations.models import MadeByType, Reservation, ReservationStatus
from modules.reservations.services import ReservationRefused, reserve
from modules.reservations.tests.factories import (
    ReservationFactory,
    approved_household,
    open_listing,
    publish_reservation_rules,
)

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 9, 15, tzinfo=UTC)  # 10:00 in Montreal


@pytest.fixture
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timezone, "now", lambda: NOW)


@pytest.fixture
def case(frozen_clock: None) -> SimpleNamespace:
    """Rules in effect, an approved household, 5 units at most 2 per household."""
    publish_reservation_rules(NOW - timedelta(days=1))
    return _case()


def _case() -> SimpleNamespace:
    household = approved_household(NOW)
    return SimpleNamespace(
        user=household.holder,
        household=household,
        listing=open_listing(NOW, quantity_total=5, max_per_household=2),
    )


def _reserve(case: SimpleNamespace, quantity: int = 1, **kwargs: Any) -> Reservation:
    values = {"listing_id": case.listing.pk, "now": NOW} | kwargs
    return reserve(case.user, case.household.pk, quantity=quantity, **values)


def _refusal(case: SimpleNamespace, quantity: int = 1, **kwargs: Any) -> str:
    """Reserve, expect a refusal, and check nothing was changed."""
    reserved_before = _units_reserved(case)
    count_before = Reservation.objects.count()
    with pytest.raises(ReservationRefused) as refused:
        _reserve(case, quantity, **kwargs)
    assert _units_reserved(case) == reserved_before
    assert Reservation.objects.count() == count_before
    return refused.value.code


def _units_reserved(case: SimpleNamespace) -> int:
    case.listing.refresh_from_db()
    return int(case.listing.quantity_reserved)


def _hold(case: SimpleNamespace, count: int, **kwargs: Any) -> None:
    """Give the household ``count`` reservations on other listings."""
    for _ in range(count):
        ReservationFactory(household=case.household, made_by=case.user, **kwargs)


# --- Acceptance criterion 1: units go down atomically ------------------------


# rule: BR-RES-009
def test_reserving_takes_the_units_and_saves_the_reservation(
    case: SimpleNamespace,
) -> None:
    reservation = _reserve(case, quantity=2)
    assert _units_reserved(case) == 2
    reservation.refresh_from_db()
    assert reservation.listing_id == case.listing.pk
    assert reservation.household_id == case.household.pk
    assert reservation.quantity == 2
    assert reservation.status == ReservationStatus.RESERVED
    assert reservation.made_by_type == MadeByType.HOUSEHOLD
    assert reservation.made_by_id == case.user.pk
    assert reservation.picked_up_at is None
    assert reservation.late_cancel is False


# rule: BR-RES-009
def test_sold_out_listing_is_refused(case: SimpleNamespace) -> None:
    case.listing.quantity_reserved = 5
    case.listing.save()
    assert _refusal(case) == services.SOLD_OUT


def test_more_than_the_units_left_is_refused(case: SimpleNamespace) -> None:
    case.listing.quantity_reserved = 4
    case.listing.save()
    assert _refusal(case, quantity=2) == services.NOT_ENOUGH_UNITS


# rule: BR-RES-009
def test_units_taken_by_someone_else_meanwhile_say_sold_out(
    case: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The listing looked open, but the conditional update found no units.
    monkeypatch.setattr(services.listing_services, "take_units", lambda *a, **k: False)
    assert _refusal(case) == services.SOLD_OUT


# --- Acceptance criterion 2: household limits ---------------------------------


# rule: BR-RES-007
def test_more_than_the_listing_max_is_refused(case: SimpleNamespace) -> None:
    assert _refusal(case, quantity=3) == services.QUANTITY_OVER_LISTING_LIMIT


# rule: BR-RES-007 in total on the listing, not per reservation.
def test_listing_max_counts_what_the_household_already_holds(
    case: SimpleNamespace,
) -> None:
    _reserve(case, quantity=1)
    assert _refusal(case, quantity=2) == services.QUANTITY_OVER_LISTING_LIMIT
    _reserve(case, quantity=1)
    assert _units_reserved(case) == 2


# rule: BR-RES-007 finished reservations do not count.
def test_listing_max_ignores_finished_reservations(case: SimpleNamespace) -> None:
    for status in ("picked_up", "cancelled", "cancelled_by_store", "no_show"):
        ReservationFactory(
            listing=case.listing, household=case.household, quantity=2, status=status
        )
    assert _reserve(case, quantity=2).quantity == 2


# rule: BR-RES-008
def test_third_active_reservation_is_allowed(case: SimpleNamespace) -> None:
    _hold(case, 2)
    assert _reserve(case).status == ReservationStatus.RESERVED


# rule: BR-RES-008
def test_fourth_active_reservation_is_refused(case: SimpleNamespace) -> None:
    _hold(case, 3)
    assert _refusal(case) == services.TOO_MANY_ACTIVE_RESERVATIONS


# rule: BR-RES-008 only reserved ones are active.
def test_finished_reservations_do_not_count_as_active(case: SimpleNamespace) -> None:
    _hold(case, 2)
    for status in ("picked_up", "cancelled", "cancelled_by_store", "no_show"):
        _hold(case, 1, status=status)
    assert _reserve(case).status == ReservationStatus.RESERVED


# rule: BR-RES-008 the limit comes from the rule setting.
def test_active_limit_follows_the_rule_setting(case: SimpleNamespace) -> None:
    # A later version, in effect since an hour ago, replaces the default of 3.
    publish_reservation_rules(NOW - timedelta(hours=1), max_active_per_household=1)
    _hold(case, 1)
    assert _refusal(case) == services.TOO_MANY_ACTIVE_RESERVATIONS


def test_other_households_do_not_count(case: SimpleNamespace) -> None:
    for _ in range(3):
        ReservationFactory(household=approved_household(NOW))
    assert _reserve(case).status == ReservationStatus.RESERVED


# --- Acceptance criterion 3: approved, not suspended, not expired -------------


# rule: BR-RES-006
@pytest.mark.parametrize(
    "changes",
    [
        {"status": "suspended"},
        {"status": "renewal_needed"},
        {"status": "submitted"},
        {"status": "rejected"},
        {"expires_at": NOW},  # expired, nightly job not run yet
    ],
)
def test_household_that_is_not_approved_is_refused(
    case: SimpleNamespace, changes: dict[str, Any]
) -> None:
    for name, value in changes.items():
        setattr(case.household, name, value)
    case.household.save()
    assert _refusal(case) == services.HOUSEHOLD_NOT_APPROVED


# --- Acceptance criterion 4: the pickup code ----------------------------------


# rule: BR-RES-010
def test_reservation_gets_a_six_character_code(case: SimpleNamespace) -> None:
    code = _reserve(case).pickup_code
    assert len(code) == 6
    assert set(code) <= set(PICKUP_CODE_ALPHABET)


# rule: BR-RES-010 a code already used on the listing is drawn again.
def test_code_clash_draws_a_new_code(case: SimpleNamespace) -> None:
    ReservationFactory(listing=case.listing, pickup_code="AAAAAA")
    letters = iter("A" * 6 + "B" * 6)

    def choose(_alphabet: Sequence[str]) -> str:
        return next(letters)

    reservation = _reserve(case, choose=choose)
    assert reservation.pickup_code == "BBBBBB"
    # The units were taken once, not once per attempt.
    assert _units_reserved(case) == 1


def test_code_that_always_clashes_gives_the_units_back(case: SimpleNamespace) -> None:
    ReservationFactory(listing=case.listing, pickup_code="AAAAAA")
    code = _refusal(case, choose=lambda _alphabet: "A")
    assert code == services.PICKUP_CODE_UNAVAILABLE


# --- The listing must be open --------------------------------------------------


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "closed"},
        {"status": "cancelled"},
        # The pickup ended, but the nightly job has not closed the listing yet.
        {"pickup_start": NOW - timedelta(hours=3), "pickup_end": NOW},
    ],
)
def test_listing_that_cannot_be_reserved_is_refused(
    case: SimpleNamespace, changes: dict[str, Any]
) -> None:
    for name, value in changes.items():
        setattr(case.listing, name, value)
    case.listing.save()
    assert _refusal(case) == services.LISTING_NOT_AVAILABLE


def test_unknown_listing_is_refused(case: SimpleNamespace) -> None:
    assert _refusal(case, listing_id=uuid.uuid4()) == services.LISTING_NOT_AVAILABLE


# --- Settings ---------------------------------------------------------------------


def test_no_reservation_rule_in_effect_is_refused(frozen_clock: None) -> None:
    assert _refusal(_case()) == services.RESERVATIONS_UNAVAILABLE


def test_rule_that_only_starts_later_is_not_used(frozen_clock: None) -> None:
    publish_reservation_rules(NOW + timedelta(hours=1))
    assert _refusal(_case()) == services.RESERVATIONS_UNAVAILABLE


def test_quantity_below_one_is_a_programming_error(case: SimpleNamespace) -> None:
    with pytest.raises(ValueError):
        _reserve(case, quantity=0)
