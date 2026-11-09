# AI contribution: 50% or more AI-generated
"""How much a household may reserve (US-41). Plain Python, no Django.

The service counts what the household already holds and passes the numbers
in; the rule values come from the ``reservations`` rule set and the listing.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

QUANTITY_OVER_LISTING_LIMIT = "quantity_over_listing_limit"
TOO_MANY_ACTIVE_RESERVATIONS = "too_many_active_reservations"


class ReservationRulesInvalid(ValueError):
    """The ``reservations`` rule values cannot be used."""


@dataclass(frozen=True)
class Holding:
    """What the household holds now, counting only ``reserved`` reservations."""

    active_reservations: int
    quantity_on_listing: int


def read_max_active(values: Mapping[str, Any]) -> int:
    """``max_active_per_household`` from the rule values, checked."""
    value = values.get("max_active_per_household") if values else None
    if type(value) is not int or value < 1:
        raise ReservationRulesInvalid("max_active_per_household must be 1 or more.")
    return value


def refusals(
    quantity: int, holding: Holding, *, max_per_household: int, max_active: int
) -> list[str]:
    """Every reason the household may not reserve ``quantity`` more units.

    An empty list means the request is within both limits. The active limit
    comes first: when both apply, it is the one the household must act on.
    """
    if quantity < 1:
        raise ValueError("quantity must be 1 or more.")
    found = []
    # rule: BR-RES-008 fewer active reservations than the setting allows.
    if holding.active_reservations >= max_active:
        found.append(TOO_MANY_ACTIVE_RESERVATIONS)
    # rule: BR-RES-007 in total on one listing, at most its max per household.
    if holding.quantity_on_listing + quantity > max_per_household:
        found.append(QUANTITY_OVER_LISTING_LIMIT)
    return found
