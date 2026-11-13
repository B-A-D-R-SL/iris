# AI contribution: 50% or more AI-generated
"""Generated reservations and approved households for tests. No real people."""

from datetime import datetime, timedelta
from typing import Any

import factory

from modules.accounts.tests.factories import UserFactory
from modules.households.tests.factories import HouseholdFactory
from modules.listings.tests.factories import ListingFactory
from modules.reservations.domain.codes import PICKUP_CODE_ALPHABET, PICKUP_CODE_LENGTH
from modules.reservations.models import MadeByType, Reservation, ReservationStatus
from modules.rules.services import publish

RESERVATION_RULES = {"max_active_per_household": 3}


def code_for(number: int) -> str:
    """A distinct, valid pickup code for each number (base 31 in the alphabet)."""
    digits = []
    for _ in range(PICKUP_CODE_LENGTH):
        number, digit = divmod(number, len(PICKUP_CODE_ALPHABET))
        digits.append(PICKUP_CODE_ALPHABET[digit])
    return "".join(reversed(digits))


def approved_household(now: datetime, holder: Any = None, **kwargs: Any) -> Any:
    """An online household file held by ``holder``, approved and valid at ``now``."""
    values: dict[str, Any] = {
        "channel": "online",
        "holder": holder if holder is not None else UserFactory(role="beneficiary"),
        "created_by": None,
        "status": "approved",
        "approved_at": now - timedelta(days=30),
        "expires_at": now + timedelta(days=335),
    }
    return HouseholdFactory(**(values | kwargs))


def open_listing(now: datetime, **kwargs: Any) -> Any:
    """A published listing whose two-hour pickup starts an hour after ``now``."""
    start = kwargs.pop("pickup_start", now + timedelta(hours=1))
    end = kwargs.pop("pickup_end", start + timedelta(hours=2))
    return ListingFactory(pickup_start=start, pickup_end=end, **kwargs)


def publish_reservation_rules(effective_from: datetime, **overrides: Any) -> None:
    """Put a ``reservations`` rule version in effect from ``effective_from``."""
    admin: Any = UserFactory(role="admin")
    publish(
        "reservations",
        RESERVATION_RULES | overrides,
        admin,
        effective_from=effective_from,
    )


class ReservationFactory(factory.django.DjangoModelFactory):
    """A live (``reserved``) reservation made by a household for itself."""

    class Meta:
        model = Reservation

    listing = factory.SubFactory(ListingFactory)
    household = factory.SubFactory(HouseholdFactory)
    quantity = 1
    pickup_code = factory.Sequence(code_for)
    status = ReservationStatus.RESERVED
    made_by_type = MadeByType.HOUSEHOLD
    made_by = factory.SubFactory(UserFactory, role="beneficiary")
