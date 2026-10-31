# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""Load the fixed fictional dataset used for local development and staging."""

import calendar
import os
import random
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from iris.seedset import (
    CITY,
    FICTIONAL_NOTE,
    POSTAL_CODE,
    SEED,
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
from modules.rules import queries as rule_queries
from modules.stores.models import Store
from modules.stores.services import ensure_badr_store

SEED_NAMESPACE = uuid.UUID("5f0e6c52-0d1a-4c9e-9d38-18a1b7a0c418")
SEED_PASSWORD_ENV = "SEED_PASSWORD"
# Local development only. Staging must set SEED_PASSWORD and never uses this default.
DEV_SEED_PASSWORD = "iris-seed-password"

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
        password = _seed_password()
        call_command("seed_rules", stdout=self.stdout)
        call_command("seed_categories", stdout=self.stdout)
        badr, _created = ensure_badr_store()
        categories = _category_choices()
        try:
            plan = build_seed_plan(categories, random.Random(SEED))
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        moment = timezone.now()
        approved_until = _approved_expiry(moment)
        stores = _ensure_stores(plan, badr)
        people = _ensure_people(plan, stores, password)
        households = _ensure_households(plan, people, moment, approved_until)
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
    seed_id = _seed_id("store", planned.email)
    existing = _existing(Store, seed_id, email=planned.email)
    if existing is not None:
        return existing
    store = Store(
        id=seed_id,
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
    saved, _created = Store.objects.get_or_create(pk=seed_id, defaults=_fields(store))
    return saved


def _ensure_people(
    plan: SeedPlan, stores: dict[int, Store], password: str
) -> dict[str, User]:
    """Create each fictional account once, without resetting a later password."""
    people: dict[str, User] = {}
    for planned in plan.people:
        store = None
        if planned.store_index is not None:
            store = stores[planned.store_index]
        people[planned.email] = _ensure_user(planned, store, password)
    return people


def _ensure_user(planned: PlannedPerson, store: Store | None, password: str) -> User:
    """Create one account. Store staff and managers must point at a store."""
    if (
        planned.role in {User.Role.STORE_STAFF, User.Role.STORE_MANAGER}
        and store is None
    ):
        raise CommandError(f"{planned.email} needs a store.")
    seed_id = _seed_id("user", planned.email)
    existing = _existing(User, seed_id, email=planned.email)
    if existing is not None:
        return existing
    user, created = User.objects.get_or_create(
        pk=seed_id,
        defaults={
            "email": planned.email,
            "password": "",
            "first_name": planned.first_name,
            "last_name": planned.last_name,
            "role": planned.role,
            "store": store,
            "preferred_language": "fr",
            "is_staff": False,
            "is_superuser": False,
        },
    )
    if created:
        user.set_password(password)
        user.save(update_fields=["password"])
    return user


def _ensure_households(
    plan: SeedPlan,
    people: dict[str, User],
    moment: Any,
    approved_until: Any,
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
            approved_until=approved_until,
        )
    return households


def _ensure_household(
    planned: PlannedHousehold,
    *,
    created_by: User,
    verified_by: User,
    moment: Any,
    approved_until: Any,
) -> Household:
    """Insert one file. A second run keeps the saved status and address."""
    seed_id = _seed_id("household", str(planned.number))
    existing = _existing(Household, seed_id, phone=planned.phone)
    if existing is not None:
        return existing

    verified = planned.status in VERIFIED_STATUSES
    approved = planned.status in APPROVED_STATUSES
    household = Household(
        id=seed_id,
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
        expires_at=_expiry(planned.status, moment, approved_until),
    )
    household.full_clean()
    saved, _created = Household.objects.get_or_create(
        pk=seed_id, defaults=_fields(household)
    )
    return saved


def _expiry(status: str, moment: Any, approved_until: Any) -> Any:
    """Renewal is already due. Approval length comes from the rules."""
    if status == HouseholdStatus.RENEWAL_NEEDED:
        return moment - timedelta(days=1)
    if status == HouseholdStatus.SUSPENDED:
        return moment + SUSPENDED_TERM
    if status == HouseholdStatus.APPROVED:
        return approved_until
    return None


def _approved_expiry(moment: Any) -> Any:
    """Use file_validity.approved_months instead of a hard-coded year."""
    rules = rule_queries.active("file_validity", at=moment)
    if rules is None:
        raise CommandError("Seed the file_validity rules before households.")
    months = rules.values.get("approved_months")
    if type(months) is not int or months < 1:
        raise CommandError("file_validity.approved_months must be a positive integer.")
    return _add_months(moment, months)


def _add_months(moment: Any, months: int) -> Any:
    """Move a timezone-aware instant forward by whole months."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


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
    seed_id = _seed_id("listing", str(planned.number))
    existing = _existing(Listing, seed_id, title=planned.title)
    if existing is not None:
        return existing
    pickup_start = moment + timedelta(days=1, minutes=planned.number)
    pickup_end = pickup_start + PICKUP_LENGTH
    listing = Listing(
        id=seed_id,
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
    saved, _created = Listing.objects.get_or_create(
        pk=seed_id, defaults=_fields(listing)
    )
    return saved


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
    """Insert one reservation. A later edit to the pickup code is kept."""
    seed_id = _seed_id("reservation", str(planned.number))
    existing = Reservation.objects.filter(pk=seed_id).first()
    if existing is None:
        existing = Reservation.objects.filter(
            listing=listing, pickup_code=planned.pickup_code
        ).first()
    if existing is not None:
        return existing
    picked_up = planned.status == ReservationStatus.PICKED_UP
    reservation = Reservation(
        id=seed_id,
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
    saved, _created = Reservation.objects.get_or_create(
        pk=seed_id, defaults=_fields(reservation)
    )
    return saved


def _seed_id(kind: str, key: str) -> uuid.UUID:
    """Stable primary key. Editing a phone, email, title, or pickup code does not change it."""
    return uuid.uuid5(SEED_NAMESPACE, f"{kind}:{key}")


def _seed_password() -> str:
    """Staging must supply SEED_PASSWORD. The default exists only for DEBUG."""
    configured = os.environ.get(SEED_PASSWORD_ENV, "").strip()
    if configured:
        return configured
    if settings.DEBUG:
        return DEV_SEED_PASSWORD
    raise CommandError("Set SEED_PASSWORD before seeding accounts when DEBUG is off.")


def _existing(model: Any, seed_id: uuid.UUID, **natural_key: Any) -> Any:
    """Find the fixed id, or a row created before those ids existed."""
    row = model.objects.filter(pk=seed_id).first()
    if row is not None:
        return row
    if not natural_key:
        return None
    return model.objects.filter(**natural_key).first()


def _fields(instance: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    """Copy concrete field values for get_or_create, skipping the primary key."""
    skipped = {"id"} | (exclude or set())
    values: dict[str, Any] = {}
    for field in instance._meta.concrete_fields:
        if field.primary_key or field.name in skipped or not field.editable:
            continue
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            continue
        values[field.attname if field.is_relation else field.name] = getattr(
            instance, field.attname if field.is_relation else field.name
        )
    return values
