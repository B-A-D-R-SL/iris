# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""The planned seed stays fixed and contains no real personal data."""

import random
from collections import Counter

import pytest

from iris.seedset import (
    HOUSEHOLD_COUNT,
    HOUSEHOLD_STATUS_COUNTS,
    LISTING_COUNT,
    LISTING_QUANTITY_TOTAL,
    RESERVATION_COUNT,
    RESERVATION_STATUS_COUNTS,
    SEED,
    CategoryChoice,
    build_seed_plan,
)

CATEGORIES = (
    CategoryChoice("bakery", True, 400),
    CategoryChoice("hygiene", False, 500),
)


def test_plan_matches_the_agreed_counts_and_repeats() -> None:
    """One seed value always produces the same fictional dataset."""
    first = build_seed_plan(CATEGORIES, random.Random(SEED))
    second = build_seed_plan(CATEGORIES, random.Random(SEED))

    assert first == second
    assert len(first.people) == 8
    assert sum(person.role == "admin" for person in first.people) == 1
    assert sum(person.role == "intake_worker" for person in first.people) == 2
    assert len(first.partner_stores) == 4
    assert len(first.households) == HOUSEHOLD_COUNT
    assert len(first.listings) == LISTING_COUNT
    assert len(first.reservations) == RESERVATION_COUNT


def test_plan_spreads_statuses_and_keeps_reservations_on_approved_files() -> None:
    """Every household status appears, and stock stays inside each listing."""
    plan = build_seed_plan(CATEGORIES, random.Random(SEED))
    household_counts = Counter(row.status for row in plan.households)
    reservation_counts = Counter(row.status for row in plan.reservations)
    approved = {row.number for row in plan.households if row.status == "approved"}
    held: Counter[int] = Counter()
    for reservation in plan.reservations:
        assert reservation.household_number in approved
        if reservation.status == "reserved":
            held[reservation.listing_number] += reservation.quantity

    assert household_counts == Counter(HOUSEHOLD_STATUS_COUNTS)
    assert reservation_counts == Counter(RESERVATION_STATUS_COUNTS)
    assert all(quantity <= LISTING_QUANTITY_TOTAL for quantity in held.values())
    assert all(row.quantity_reserved == held[row.number] for row in plan.listings)


def test_plan_uses_only_fictional_contact_details() -> None:
    """Emails, names, and phones are placeholders, not real people."""
    plan = build_seed_plan(CATEGORIES, random.Random(SEED))

    assert {person.first_name for person in plan.people} == {"Exemple"}
    for person in plan.people:
        assert person.email.endswith("@example.test")
    for store in plan.partner_stores:
        assert store.email.endswith("@example.test")
        assert "555" in store.phone
    for household in plan.households:
        assert household.phone.startswith("+1514555")
        assert "exemple" in household.address_key


def test_plan_refuses_to_invent_categories() -> None:
    """Listings need the category seed. An empty list is a setup error."""
    with pytest.raises(ValueError, match="category"):
        build_seed_plan((), random.Random(SEED))
