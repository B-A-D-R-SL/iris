# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""manage.py seed loads the agreed dataset and can be run again safely."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.db.models import Sum
from django.utils import timezone

from iris.seedset import (
    HOUSEHOLD_STATUS_COUNTS,
    RESERVATION_STATUS_COUNTS,
    SEED_PASSWORD,
)
from modules.accounts.models import User
from modules.households.models import Household, HouseholdStatus
from modules.listings.models import Listing
from modules.reservations.models import Reservation, ReservationStatus
from modules.rules.domain.schemas import RULE_TYPES
from modules.rules.management.commands.seed_rules import SEED_USERNAME
from modules.rules.models import RuleSetVersion
from modules.stores.models import Store
from modules.stores.services import ensure_badr_store


@pytest.mark.django_db
def test_seed_fills_an_empty_database_and_keeps_later_edits() -> None:
    """Empty database and a second run on existing rows both succeed."""
    store, _created = ensure_badr_store()
    store.pickup_instructions = "Déjà modifié sur le staging."
    store.save(update_fields=["pickup_instructions"])

    call_command("seed", stdout=StringIO())

    admin = User.objects.get(email="coordonnateur@example.test")
    assert admin.role == User.Role.ADMIN
    assert admin.check_password(SEED_PASSWORD)
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
    for status, count in HOUSEHOLD_STATUS_COUNTS.items():
        assert Household.objects.filter(status=status).count() == count
    for status, count in RESERVATION_STATUS_COUNTS.items():
        assert Reservation.objects.filter(status=status).count() == count
    assert not Reservation.objects.exclude(
        household__status=HouseholdStatus.APPROVED
    ).exists()
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

    for email in User.objects.values_list("email", flat=True):
        assert email.endswith("@example.test") or email == SEED_USERNAME
    assert "555" in Store.objects.get(is_badr=True).phone
    assert all(
        "555" in phone for phone in Household.objects.values_list("phone", flat=True)
    )

    store.refresh_from_db()
    assert store.pickup_instructions == "Déjà modifié sur le staging."
    household = Household.objects.get(phone="+15145551001")
    household.city = "Laval"
    household.save(update_fields=["city"])
    partner = Store.objects.get(email="commerce-exemple-1@example.test")
    partner.name = "Nom modifié"
    partner.save(update_fields=["name"])

    call_command("seed", stdout=StringIO())

    assert Household.objects.count() == 50
    assert Listing.objects.count() == 30
    assert Reservation.objects.count() == 40
    assert Store.objects.filter(is_badr=True).count() == 1
    household.refresh_from_db()
    partner.refresh_from_db()
    store.refresh_from_db()
    assert household.city == "Laval"
    assert partner.name == "Nom modifié"
    assert store.pickup_instructions == "Déjà modifié sur le staging."
