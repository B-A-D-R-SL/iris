# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""Load the fixed fictional dataset used for local development and staging."""

import random
from datetime import timedelta
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from iris.seedset import (
    CITY,
    FICTIONAL_NOTE,
    POSTAL_CODE,
    SEED,
    SEED_PASSWORD,
    STREET_NAME,
    CategoryChoice,
    PlannedHousehold,
    PlannedListing,
    PlannedPerson,
    PlannedReservation,
    PlannedStore,
    SeedPlan,
    build_seed_plan,
)
from modules.accounts.models import User
from modules.categories.models import Category
from modules.households.models import Household, HouseholdStatus
from modules.listings.models import Listing, ListingStatus
from modules.reservations.models import MadeByType, Reservation, ReservationStatus
from modules.stores.models import Store
from modules.stores.services import ensure_badr_store

APPROVED_STATUSES = frozenset(
    {
        HouseholdStatus.APPROVED,
        HouseholdStatus.RENEWAL_NEEDED,
        HouseholdStatus.SUSPENDED,
    }
)
VERIFIED_STATUSES = frozenset(
    {
        HouseholdStatus.REVIEW_REQUIRED,
        HouseholdStatus.AWAITING_VISIT,
        HouseholdStatus.APPROVED,
        HouseholdStatus.RENEWAL_NEEDED,
        HouseholdStatus.SUSPENDED,
        HouseholdStatus.REJECTED,
    }
)
OPENING_HOURS = {"monday": "09:00-17:00"}
PICKUP_LENGTH = timedelta(hours=2)
APPROVAL_AGE = timedelta(days=30)
APPROVAL_TERM = timedelta(days=365)
SUSPENDED_TERM = timedelta(days=30)


class Command(BaseCommand):
    """Create the agreed demo rows without overwriting later edits."""

    help = (
        "Seed fictional admin, intake workers, stores, households, listings, "
        "and reservations. Safe to run again, including on staging."
    )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        """Fill an empty database, or add only the rows that are still missing."""
        call_command("seed_rules", stdout=self.stdout)
        call_command("seed_categories", stdout=self.stdout)
        badr, _created = ensure_badr_store()
        categories = _category_choices()
        try:
            plan = build_seed_plan(categories, random.Random(SEED))
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        moment = timezone.now()
        stores = _ensure_stores(plan, badr)
        people = _ensure_people(plan, stores)
        households = _ensure_households(plan, people, moment)
        listings = _ensure_listings(plan, stores, people, moment)
        _ensure_reservations(plan, listings, households, people, moment)
        self.stdout.write(
            self.style.SUCCESS(
                "Seed data ready: 1 admin, 2 intake workers, "
                "B.A.D.R. and 4 partner stores, 50 households, "
                "30 listings, 40 reservations."
            )
        )


def _category_choices() -> tuple[CategoryChoice, ...]:
    """Read active categories in a stable order for the fixed random draw."""
    rows = tuple(
        CategoryChoice(
            code=category.code,
            is_food=category.is_food,
            default_value_cents=category.default_value_cents,
        )
        for category in Category.objects.filter(is_active=True).order_by("code")
    )
    if not rows:
        raise CommandError("Seed categories before creating listings.")
    return rows


def _ensure_stores(plan: SeedPlan, badr: Store) -> dict[int, Store]:
    """Keep the B.A.D.R. store and create each fictional partner once."""
    stores = {0: badr}
    for index, planned in enumerate(plan.partner_stores, start=1):
        stores[index] = _ensure_partner(planned)
    return stores


def _ensure_partner(planned: PlannedStore) -> Store:
    """Create one partner, leaving an existing row and its edits in place."""
    existing = Store.objects.filter(email=planned.email).first()
    if existing is not None:
        return existing
    store = Store(
        name=planned.name,
        email=planned.email,
        phone=planned.phone,
        street_number=planned.street_number,
        street_name=STREET_NAME,
        city=CITY,
        postal_code=POSTAL_CODE,
        opening_hours=OPENING_HOURS,
        pickup_instructions=FICTIONAL_NOTE,
        is_badr=False,
        is_active=True,
    )
    store.full_clean()
    store.save()
    return store


def _ensure_people(plan: SeedPlan, stores: dict[int, Store]) -> dict[str, User]:
    """Create each fictional account once, without resetting a later password."""
    people: dict[str, User] = {}
    for planned in plan.people:
        store = None
        if planned.store_index is not None:
            store = stores[planned.store_index]
        people[planned.email] = _ensure_user(planned, store)
    return people


def _ensure_user(planned: PlannedPerson, store: Store | None) -> User:
    """Create one account. Store staff and managers must point at a store."""
    existing = User.objects.filter(email=planned.email).first()
    if existing is not None:
        return existing
    if (
        planned.role in {User.Role.STORE_STAFF, User.Role.STORE_MANAGER}
        and store is None
    ):
        raise CommandError(f"{planned.email} needs a store.")
    is_admin = planned.role == User.Role.ADMIN
    return User.objects.create_user(
        planned.email,
        SEED_PASSWORD,
        first_name=planned.first_name,
        last_name=planned.last_name,
        role=planned.role,
        store=store,
        preferred_language="fr",
        is_staff=is_admin,
        is_superuser=is_admin,
    )


def _ensure_households(
    plan: SeedPlan, people: dict[str, User], moment: Any
) -> dict[int, Household]:
    """Create each fictional file once."""
    intake = [
        people[person.email]
        for person in plan.people
        if person.role == User.Role.INTAKE_WORKER
    ]
    households: dict[int, Household] = {}
    for planned in plan.households:
        households[planned.number] = _ensure_household(
            planned,
            created_by=intake[(planned.number - 1) % len(intake)],
            verified_by=intake[planned.number % len(intake)],
            moment=moment,
        )
    return households


def _ensure_household(
    planned: PlannedHousehold,
    *,
    created_by: User,
    verified_by: User,
    moment: Any,
) -> Household:
    """Insert one file. A second run keeps the saved status and address."""
    existing = Household.objects.filter(phone=planned.phone).first()
    if existing is not None:
        return existing

    verified = planned.status in VERIFIED_STATUSES
    approved = planned.status in APPROVED_STATUSES
    household = Household(
        channel=planned.channel,
        status=planned.status,
        street_number=planned.street_number,
        street_name=STREET_NAME,
        city=CITY,
        postal_code=POSTAL_CODE,
        address_key=planned.address_key,
        phone=planned.phone,
        created_by=created_by,
        verified_by=verified_by if verified else None,
        verified_at=moment if verified else None,
        approved_at=moment - APPROVAL_AGE if approved else None,
        expires_at=_expiry(planned.status, moment),
    )
    household.full_clean()
    household.save()
    return household


def _expiry(status: str, moment: Any) -> Any:
    """Renewal is already due. Suspension ends sooner than a normal approval."""
    if status == HouseholdStatus.RENEWAL_NEEDED:
        return moment - timedelta(days=1)
    if status == HouseholdStatus.SUSPENDED:
        return moment + SUSPENDED_TERM
    if status == HouseholdStatus.APPROVED:
        return moment + APPROVAL_TERM
    return None


def _ensure_listings(
    plan: SeedPlan,
    stores: dict[int, Store],
    people: dict[str, User],
    moment: Any,
) -> dict[int, Listing]:
    """Create each fictional offer once."""
    by_code = {category.code: category for category in Category.objects.all()}
    staff = {
        person.store_index: people[person.email]
        for person in plan.people
        if person.store_index is not None
    }
    listings: dict[int, Listing] = {}
    for planned in plan.listings:
        listings[planned.number] = _ensure_listing(
            planned,
            store=stores[planned.store_index],
            category=by_code[planned.category_code],
            staff=staff[planned.store_index],
            moment=moment,
        )
    return listings


def _ensure_listing(
    planned: PlannedListing,
    *,
    store: Store,
    category: Category,
    staff: User,
    moment: Any,
) -> Listing:
    """Insert one published offer. Later edits to that title are kept."""
    existing = Listing.objects.filter(title=planned.title).first()
    if existing is not None:
        return existing
    pickup_start = moment + timedelta(days=1, minutes=planned.number)
    pickup_end = pickup_start + PICKUP_LENGTH
    listing = Listing(
        store=store,
        category=category,
        title=planned.title,
        description=FICTIONAL_NOTE,
        quantity_total=planned.quantity_total,
        quantity_reserved=planned.quantity_reserved,
        unit="item",
        max_per_household=2,
        pickup_start=pickup_start,
        pickup_end=pickup_end,
        best_before=timezone.localdate(pickup_end) if planned.is_food else None,
        estimated_value_cents=planned.estimated_value_cents,
        status=ListingStatus.PUBLISHED,
        safe_confirmed_by=staff,
        safe_confirmed_at=moment,
        published_at=moment,
        created_by=staff,
    )
    listing.full_clean()
    listing.save()
    return listing


def _ensure_reservations(
    plan: SeedPlan,
    listings: dict[int, Listing],
    households: dict[int, Household],
    people: dict[str, User],
    moment: Any,
) -> None:
    """Create each fictional reservation once."""
    staff = {
        person.store_index: people[person.email]
        for person in plan.people
        if person.store_index is not None
    }
    listing_store = {row.number: row.store_index for row in plan.listings}
    for planned in plan.reservations:
        _ensure_reservation(
            planned,
            listing=listings[planned.listing_number],
            household=households[planned.household_number],
            staff=staff[listing_store[planned.listing_number]],
            moment=moment,
        )


def _ensure_reservation(
    planned: PlannedReservation,
    *,
    listing: Listing,
    household: Household,
    staff: User,
    moment: Any,
) -> Reservation:
    """Insert one reservation. The pickup code stays unique on its listing."""
    existing = Reservation.objects.filter(
        listing=listing, pickup_code=planned.pickup_code
    ).first()
    if existing is not None:
        return existing
    picked_up = planned.status == ReservationStatus.PICKED_UP
    reservation = Reservation(
        listing=listing,
        household=household,
        quantity=planned.quantity,
        pickup_code=planned.pickup_code,
        status=planned.status,
        late_cancel=planned.status == ReservationStatus.CANCELLED,
        made_by_type=MadeByType.STAFF,
        made_by=staff,
        picked_up_at=moment if picked_up else None,
        confirmed_by=staff if picked_up else None,
    )
    reservation.full_clean()
    reservation.save()
    return reservation
