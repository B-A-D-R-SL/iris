# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""Fixed fictional dataset planned by python manage.py seed.

The random generator is created with SEED so every run plans the same rows.
Nothing here is a real person, phone, or address.
"""

import random
from collections import Counter
from dataclasses import dataclass

SEED = 18
HOUSEHOLD_COUNT = 50
LISTING_COUNT = 30
RESERVATION_COUNT = 40
PARTNER_STORE_COUNT = 4
LISTING_QUANTITY_TOTAL = 8
RESERVATION_QUANTITY = 1
STORE_COUNT = PARTNER_STORE_COUNT + 1
FICTIONAL_NOTE = "Donnée fictive pour la démonstration."
POSTAL_CODE = "H0H 0H0"
STREET_NAME = "rue Exemple"
CITY = "Montreal"

HOUSEHOLD_STATUS_COUNTS = {
    "draft": 6,
    "submitted": 7,
    "review_required": 6,
    "awaiting_visit": 6,
    "approved": 7,
    "renewal_needed": 6,
    "suspended": 6,
    "rejected": 6,
}
RESERVATION_STATUS_COUNTS = {
    "reserved": 20,
    "picked_up": 8,
    "cancelled": 4,
    "cancelled_by_store": 4,
    "no_show": 4,
}
WALK_IN = "walk-in"
ONLINE = "online"


@dataclass(frozen=True)
class CategoryChoice:
    """One active category the planner can assign to a listing."""

    code: str
    is_food: bool
    default_value_cents: int


@dataclass(frozen=True)
class PlannedPerson:
    """A fictional account. store_index 0 is B.A.D.R.; 1–4 are partners."""

    email: str
    first_name: str
    last_name: str
    role: str
    store_index: int | None


@dataclass(frozen=True)
class PlannedStore:
    """A fictional partner store. B.A.D.R. itself is created by its own seed."""

    name: str
    email: str
    phone: str
    street_number: str


@dataclass(frozen=True)
class PlannedHousehold:
    """One fictional household file."""

    number: int
    status: str
    channel: str
    phone: str
    street_number: str
    address_key: str


@dataclass(frozen=True)
class PlannedListing:
    """One fictional listing."""

    number: int
    store_index: int
    category_code: str
    is_food: bool
    estimated_value_cents: int
    title: str
    quantity_total: int
    quantity_reserved: int


@dataclass(frozen=True)
class PlannedReservation:
    """One fictional reservation. household_number points at an approved file."""

    number: int
    listing_number: int
    household_number: int
    status: str
    quantity: int
    pickup_code: str


@dataclass(frozen=True)
class SeedPlan:
    """The whole agreed dataset, before it is written to the database."""

    people: tuple[PlannedPerson, ...]
    partner_stores: tuple[PlannedStore, ...]
    households: tuple[PlannedHousehold, ...]
    listings: tuple[PlannedListing, ...]
    reservations: tuple[PlannedReservation, ...]


def build_seed_plan(
    categories: tuple[CategoryChoice, ...] | list[CategoryChoice],
    rng: random.Random,
) -> SeedPlan:
    """Build the agreed counts. The same seed and categories always match."""
    choices = tuple(categories)
    if not choices:
        raise ValueError("At least one category is required.")

    households = _households()
    approved = [row.number for row in households if row.status == "approved"]
    if not approved:
        raise ValueError("The seed needs at least one approved household.")
    rng.shuffle(approved)

    reservations = _reservations(approved)
    reserved_units = Counter(
        {listing_number: 0 for listing_number in range(1, LISTING_COUNT + 1)}
    )
    for reservation in reservations:
        if reservation.status == "reserved":
            reserved_units[reservation.listing_number] += reservation.quantity

    listings = _listings(choices, rng, reserved_units)
    return SeedPlan(
        people=_people(),
        partner_stores=_partner_stores(),
        households=households,
        listings=listings,
        reservations=reservations,
    )


def _expand(counts: dict[str, int]) -> tuple[str, ...]:
    """Repeat each status in dict order so the spread is stable."""
    return tuple(status for status, count in counts.items() for _ in range(count))


def _people() -> tuple[PlannedPerson, ...]:
    """One admin, two intake workers, and one staff account per store."""
    people = [
        PlannedPerson(
            "coordonnateur@example.test",
            "Exemple",
            "Coordonnateur",
            "admin",
            None,
        ),
        PlannedPerson(
            "accueil-1@example.test", "Exemple", "Accueil", "intake_worker", None
        ),
        PlannedPerson(
            "accueil-2@example.test", "Exemple", "Accueil", "intake_worker", None
        ),
        PlannedPerson(
            "personnel-badr@example.test",
            "Exemple",
            "Personnel",
            "store_staff",
            0,
        ),
    ]
    for index in range(1, PARTNER_STORE_COUNT + 1):
        people.append(
            PlannedPerson(
                f"gerant-exemple-{index}@example.test",
                "Exemple",
                "Gerant",
                "store_manager",
                index,
            )
        )
    return tuple(people)


def _partner_stores() -> tuple[PlannedStore, ...]:
    """Four fictional partners. Numbers stay inside the 555 range."""
    return tuple(
        PlannedStore(
            name=f"Commerce exemple {index}",
            email=f"commerce-exemple-{index}@example.test",
            phone=f"+1514555020{index}",
            street_number=str(index),
        )
        for index in range(1, PARTNER_STORE_COUNT + 1)
    )


def _households() -> tuple[PlannedHousehold, ...]:
    """Fifty files spread across every household status."""
    statuses = _expand(HOUSEHOLD_STATUS_COUNTS)
    rows: list[PlannedHousehold] = []
    for number, status in enumerate(statuses, start=1):
        street_number = str(number)
        rows.append(
            PlannedHousehold(
                number=number,
                status=status,
                channel=WALK_IN if number % 2 else ONLINE,
                phone=f"+15145551{number:03d}",
                street_number=street_number,
                address_key=(f"{street_number}|rue exemple||montreal|h0h 0h0"),
            )
        )
    return tuple(rows)


def _listings(
    categories: tuple[CategoryChoice, ...],
    rng: random.Random,
    reserved_units: Counter[int],
) -> tuple[PlannedListing, ...]:
    """Thirty listings, six on each of the five stores."""
    rows: list[PlannedListing] = []
    for number in range(1, LISTING_COUNT + 1):
        category = categories[rng.randrange(len(categories))]
        rows.append(
            PlannedListing(
                number=number,
                store_index=(number - 1) % STORE_COUNT,
                category_code=category.code,
                is_food=category.is_food,
                estimated_value_cents=category.default_value_cents,
                title=f"Offre exemple {number:02d}",
                quantity_total=LISTING_QUANTITY_TOTAL,
                quantity_reserved=reserved_units[number],
            )
        )
    return tuple(rows)


def _reservations(
    approved_households: list[int],
) -> tuple[PlannedReservation, ...]:
    """Forty reservations, and only on approved household files."""
    statuses = _expand(RESERVATION_STATUS_COUNTS)
    return tuple(
        PlannedReservation(
            number=number,
            listing_number=((number - 1) % LISTING_COUNT) + 1,
            household_number=approved_households[
                (number - 1) % len(approved_households)
            ],
            status=status,
            quantity=RESERVATION_QUANTITY,
            pickup_code=f"{number:06d}",
        )
        for number, status in enumerate(statuses, start=1)
    )
