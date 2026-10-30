# AI contribution: 50% or more AI-generated
"""Posting input and pure validation; limits are supplied by versioned rules."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

MINIMUM_POSITIVE_INTEGER = 1
ALLOWED_UNITS = frozenset({"item", "bundle"})


@dataclass(frozen=True)
class ListingInput:
    category: str  # the category's stable code, for example "bakery"
    title: str
    quantity: int
    pickup_start: datetime
    pickup_end: datetime
    safe_and_allowed: bool
    description: str | None = None
    unit: str = "item"
    max_per_household: int = 1
    best_before: date | None = None
    estimated_value_cents: int | None = None


@dataclass(frozen=True)
class PostingLimits:
    title_min_length: int
    title_max_length: int
    description_max_length: int
    quantity_max: int
    max_per_household: int
    estimated_value_max_cents: int
    pickup_start_max_days: int
    pickup_min_minutes: int
    pickup_max_minutes: int
    photo_max_bytes: int
    photo_max_dimension: int


@dataclass(frozen=True)
class Refusal:
    """A field and stable reason code; translation belongs outside the domain."""

    field: str
    code: str


def check_posting(
    data: ListingInput, limits: PostingLimits, *, now: datetime
) -> list[Refusal]:
    """Check US-33 fields without a framework, database, clock or file store."""
    if now.utcoffset() is None:
        raise ValueError("The supplied clock must be timezone-aware.")

    refusals: list[Refusal] = []
    if (
        not limits.title_min_length
        <= len(data.title.strip())
        <= limits.title_max_length
    ):
        refusals.append(Refusal("title", "title_length"))
    if (
        data.description is not None
        and len(data.description) > limits.description_max_length
    ):
        refusals.append(Refusal("description", "description_length"))
    if type(data.quantity) is not int or not (
        MINIMUM_POSITIVE_INTEGER <= data.quantity <= limits.quantity_max
    ):
        refusals.append(Refusal("quantity", "quantity_range"))
    if data.unit not in ALLOWED_UNITS:
        refusals.append(Refusal("unit", "unit_choice"))
    if type(data.max_per_household) is not int or not (
        MINIMUM_POSITIVE_INTEGER <= data.max_per_household <= limits.max_per_household
    ):
        refusals.append(Refusal("max_per_household", "household_range"))
    if data.estimated_value_cents is not None and (
        type(data.estimated_value_cents) is not int
        or not 0 <= data.estimated_value_cents <= limits.estimated_value_max_cents
    ):
        refusals.append(Refusal("estimated_value_cents", "value_range"))
    if data.safe_and_allowed is not True:
        refusals.append(Refusal("safe_and_allowed", "confirmation_required"))

    if data.pickup_start.utcoffset() is None:
        refusals.append(Refusal("pickup_start", "timezone_required"))
    if data.pickup_end.utcoffset() is None:
        refusals.append(Refusal("pickup_end", "timezone_required"))
    if any(reason.code == "timezone_required" for reason in refusals):
        return refusals

    # Normalize before subtraction so DST changes use elapsed time.
    start = data.pickup_start.astimezone(UTC)
    end = data.pickup_end.astimezone(UTC)
    instant = now.astimezone(UTC)
    if not instant <= start <= instant + timedelta(days=limits.pickup_start_max_days):
        refusals.append(Refusal("pickup_start", "pickup_start_range"))
    if not (
        timedelta(minutes=limits.pickup_min_minutes)
        <= end - start
        <= timedelta(minutes=limits.pickup_max_minutes)
    ):
        refusals.append(Refusal("pickup_end", "pickup_duration"))
    return refusals


def safety_payload(data: ListingInput) -> dict[str, Any]:
    """Explicit input for US-34's check(listing_data, category, rules) contract."""
    return {
        "category": data.category,
        "title": data.title,
        "quantity_total": data.quantity,
        "pickup_start": data.pickup_start,
        "pickup_end": data.pickup_end,
        "best_before": data.best_before,
        "safe_and_allowed": data.safe_and_allowed,
    }
