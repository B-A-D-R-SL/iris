# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""manage.py seed loads the agreed dataset and can be run again safely."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.utils import timezone

from iris.management.commands.seed import APPROVAL_AGE, _add_months
from iris.seedset import HOUSEHOLD_STATUS_COUNTS, RESERVATION_STATUS_COUNTS
from modules.accounts.models import User
from modules.households.models import Household, HouseholdStatus
from modules.listings.models import Listing
from modules.reservations.models import Reservation, ReservationStatus
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES, RULE_TYPES
from modules.rules.management.commands.seed_rules import SEED_USERNAME
from modules.rules.models import RuleSetVersion
from modules.stores.models import Store
from modules.stores.services import ensure_badr_store

TEST_PASSWORD = "iris-seed-password"


@pytest.fixture
def seed_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests run with DEBUG off, so the password has to come from the environment."""
    monkeypatch.setenv("SEED_PASSWORD", TEST_PASSWORD)


@pytest.fixture
def seeded(seed_password: None) -> None:
    """Load the dataset once for a test that only reads it."""
    call_command("seed", stdout=StringIO())


@pytest.mark.django_db
def test_seed_creates_the_agreed_counts_on_an_empty_database(seeded: None) -> None:
    """One admin, two intake workers, five stores, and the agreed row counts."""
    assert User.objects.filter(role=User.Role.ADMIN, is_superuser=False).count() == 1
    assert User.objects.filter(role=User.Role.INTAKE_WORKER).count() == 2
    assert (
        User.objects.filter(role=User.Role.STORE_STAFF, store__is_badr=True).count()
        == 1
    )
    assert User.objects.filter(role=User.Role.STORE_MANAGER).count() == 4
    assert Store.objects.filter(is_badr=True).count() == 1
    assert Store.objects.filter(is_badr=False).count() == 4
    assert Household.objects.count() == 50
    assert Listing.objects.count() == 30
    assert Reservation.objects.count() == 40
    assert RuleSetVersion.objects.filter(version=1).count() == len(RULE_TYPES)


@pytest.mark.django_db
def test_seed_spreads_household_and_reservation_statuses(seeded: None) -> None:
    """Every status is present, and reservations stay on approved files."""
    for status, count in HOUSEHOLD_STATUS_COUNTS.items():
        assert Household.objects.filter(status=status).count() == count
    for status, count in RESERVATION_STATUS_COUNTS.items():
        assert Reservation.objects.filter(status=status).count() == count
    assert not Reservation.objects.exclude(
        household__status=HouseholdStatus.APPROVED
    ).exists()


@pytest.mark.django_db
def test_approved_household_expiry_follows_file_validity(seeded: None) -> None:
    """Approved files last for file_validity.approved_months, not a fixed year."""
    household = Household.objects.filter(status=HouseholdStatus.APPROVED).first()
    assert household is not None and household.approved_at is not None
    months = DEFAULT_RULE_VALUES["file_validity"]["approved_months"]
    moment = household.approved_at + APPROVAL_AGE
    assert household.expires_at == _add_months(moment, months)


@pytest.mark.django_db
def test_seed_keeps_listing_stock_equal_to_reserved_quantity(seeded: None) -> None:
    """Reserved stock matches reservations that are still reserved."""
    for listing in Listing.objects.all():
        held = (
            listing.reservations.filter(status=ReservationStatus.RESERVED).aggregate(
                total=Sum("quantity")
            )["total"]
            or 0
        )
        assert listing.quantity_reserved == held
        if listing.category.is_food:
            assert listing.best_before is not None
            assert listing.best_before >= timezone.localdate(listing.pickup_end)
        else:
            assert listing.best_before is None


@pytest.mark.django_db
def test_seed_uses_only_fictional_contact_details(seeded: None) -> None:
    """Emails and phones are placeholders."""
    for email in User.objects.values_list("email", flat=True):
        assert email.endswith("@example.test") or email == SEED_USERNAME
    assert "555" in Store.objects.get(is_badr=True).phone
    assert all(
        "555" in phone for phone in Household.objects.values_list("phone", flat=True)
    )


@pytest.mark.django_db
def test_seed_user_can_sign_in(seeded: None) -> None:
    """The seed admin can sign in and is not a Django superuser."""
    admin = User.objects.get(email="coordonnateur@example.test")
    assert admin.role == User.Role.ADMIN
    assert admin.is_superuser is False
    assert admin.is_staff is False
    assert admin.check_password(TEST_PASSWORD)


@pytest.mark.django_db
def test_second_seed_run_adds_no_rows(seeded: None) -> None:
    """A repeat run leaves the counts unchanged."""
    call_command("seed", stdout=StringIO())

    assert Household.objects.count() == 50
    assert Listing.objects.count() == 30
    assert Reservation.objects.count() == 40
    assert Store.objects.filter(is_badr=False).count() == 4


@pytest.mark.django_db
def test_second_seed_run_keeps_edited_rows(seed_password: None) -> None:
    """Edits to a phone, title, email, address, or pickup code survive the next run."""
    store, _created = ensure_badr_store()
    store.pickup_instructions = "Déjà modifié sur le staging."
    store.save(update_fields=["pickup_instructions"])
    call_command("seed", stdout=StringIO())

    household = Household.objects.get(phone="+15145551001")
    household.phone = "+15145559999"
    household.city = "Laval"
    household.save(update_fields=["phone", "city"])
    listing = Listing.objects.get(title="Offre exemple 01")
    listing.title = "Titre modifié"
    listing.save(update_fields=["title"])
    partner = Store.objects.get(email="commerce-exemple-1@example.test")
    partner.email = "modifie@example.test"
    partner.name = "Nom modifié"
    partner.save(update_fields=["email", "name"])
    reservation = Reservation.objects.get(pickup_code="000001")
    reservation.pickup_code = "ZZZZZZ"
    reservation.save(update_fields=["pickup_code"])

    call_command("seed", stdout=StringIO())

    assert Household.objects.count() == 50
    assert Listing.objects.count() == 30
    assert Reservation.objects.count() == 40
    assert Store.objects.filter(is_badr=False).count() == 4
    household.refresh_from_db()
    listing.refresh_from_db()
    partner.refresh_from_db()
    store.refresh_from_db()
    assert household.phone == "+15145559999"
    assert household.city == "Laval"
    assert listing.title == "Titre modifié"
    assert partner.email == "modifie@example.test"
    assert partner.name == "Nom modifié"
    reservation.refresh_from_db()
    assert reservation.pickup_code == "ZZZZZZ"
    assert store.pickup_instructions == "Déjà modifié sur le staging."


@pytest.mark.django_db
def test_seed_refuses_accounts_without_a_password_when_debug_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Staging must set SEED_PASSWORD. The development default stays off."""
    monkeypatch.delenv("SEED_PASSWORD", raising=False)

    with pytest.raises(CommandError, match="SEED_PASSWORD"):
        call_command("seed", stdout=StringIO())


def test_add_months_clamps_the_day() -> None:
    """31 January plus one month lands on the last day of February."""
    moment = timezone.now().replace(year=2026, month=1, day=31)
    assert _add_months(moment, 1) == moment.replace(month=2, day=28)
    assert _add_months(moment, 12).year == 2027
