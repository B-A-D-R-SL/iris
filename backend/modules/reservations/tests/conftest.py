# AI contribution: 50% or more AI-generated
"""US-44 fixtures: two stores, their staff, and one open pickup at the first store."""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from itertools import count
from types import SimpleNamespace
from typing import Any, cast

import pytest
from django.utils import timezone, translation

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household, Member
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.listings.models import Listing
from modules.listings.tests.factories import ListingFactory
from modules.reservations.models import MadeByType, Reservation, ReservationStatus
from modules.stores.tests.factories import StoreFactory

# 16:30 in Montreal, inside a 16:00 to 18:00 pickup window.
NOW = datetime(2026, 11, 7, 21, 30, tzinfo=UTC)
WINDOW_START = NOW - timedelta(minutes=30)
WINDOW_END = NOW + timedelta(minutes=90)

_codes = count(1)


def next_code() -> str:
    """A distinct code in the pickup alphabet (no O, 0, I, L or 1)."""
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    number, digits = next(_codes), []
    for _ in range(6):
        number, digit = divmod(number, len(alphabet))
        digits.append(alphabet[digit])
    return "".join(reversed(digits))


def open_listing(store: Any, **kwargs: Any) -> Listing:
    """A listing at ``store`` whose pickup window contains NOW."""
    kwargs.setdefault("pickup_start", WINDOW_START)
    kwargs.setdefault("pickup_end", WINDOW_END)
    return cast(
        Listing, ListingFactory(store=store, title="Pain de la veille", **kwargs)
    )


def pickup_household(alternate_name: str = "Paul Tremblay") -> Household:
    """A household with holder Fatou Diallo; no contact detail leaves it at pickup."""
    household = cast(Household, HouseholdFactory(alternate_name=alternate_name))
    MemberFactory(
        household=household,
        first_name="Fatou",
        last_name="Diallo",
        relation=Member.Relation.HOLDER,
    )
    return household


@pytest.fixture
def make_reservation(
    pickup_case: SimpleNamespace,
) -> Callable[..., Reservation]:
    """Create a reservation; any field can be overridden."""

    def make(**kwargs: Any) -> Reservation:
        values: dict[str, Any] = {
            "listing": pickup_case.listing,
            "household": pickup_case.household,
            "quantity": 2,
            "pickup_code": next_code(),
            "status": ReservationStatus.RESERVED,
            "made_by_type": MadeByType.HOUSEHOLD,
            "made_by": pickup_case.beneficiary,
        }
        values.update(kwargs)
        return Reservation.objects.create(**values)

    return make


@pytest.fixture
def pickup_case(db: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    store, other_store = StoreFactory(), StoreFactory()
    case = SimpleNamespace(
        now=NOW,
        store=store,
        other_store=other_store,
        staff=UserFactory(role=User.Role.STORE_STAFF, store=store),
        manager=UserFactory(role=User.Role.STORE_MANAGER, store=store),
        other_staff=UserFactory(role=User.Role.STORE_STAFF, store=other_store),
        beneficiary=UserFactory(role=User.Role.BENEFICIARY),
        listing=open_listing(store),
        other_listing=open_listing(other_store),
        household=pickup_household(),
    )
    with translation.override("en"):
        yield case
