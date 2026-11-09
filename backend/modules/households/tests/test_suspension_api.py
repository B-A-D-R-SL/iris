# AI contribution: 50% or more AI-generated
"""US-32 suspension transitions, reservation cancellation and authorization."""

from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory
from modules.listings.models import Listing
from modules.listings.tests.factories import ListingFactory
from modules.reservations.models import MadeByType, Reservation, ReservationStatus
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


def url(household: Household, action: str) -> str:
    return reverse(f"staff-households-{action}", kwargs={"id": household.pk})


def approved(**changes: Any) -> Household:
    values = {
        "status": Household.Status.APPROVED,
        "approved_at": timezone.now() - timedelta(days=1),
        "expires_at": timezone.now() + timedelta(days=30),
        "email": "holder@example.test",
        "preferred_language": "en",
    }
    values.update(changes)
    return cast(Household, HouseholdFactory(**values))


def post(actor: Any, household: Household, action: str, reason: str = "Safety review"):
    client = APIClient()
    if actor is not None:
        client.force_authenticate(actor)
    return client.post(url(household, action), {"reason": reason}, format="json")


def test_admin_suspends_and_reactivates_with_audits() -> None:
    admin = UserFactory(role="admin")
    household = approved()
    expiry = household.expires_at

    suspended = post(admin, household, "suspend")
    assert suspended.status_code == 200
    assert suspended.data["id"] == str(household.pk)
    assert suspended.data["status"] == "suspended"
    assert suspended.data["status_reason"] == "Safety review"
    assert datetime.fromisoformat(suspended.data["expires_at"]) == expiry

    reactivated = post(admin, household, "reactivate", "Review completed")
    assert reactivated.status_code == 200
    household.refresh_from_db()
    assert household.status == Household.Status.APPROVED
    assert household.status_reason == ""
    assert household.expires_at == expiry
    assert list(
        AuditEvent.objects.filter(target_id=str(household.pk)).values_list(
            "action", "metadata"
        )
    ) == [
        ("suspend", {"reason": "Safety review"}),
        ("reactivate", {"reason": "Review completed"}),
    ]


def test_suspending_cancels_open_reservations_and_returns_units() -> None:
    admin = UserFactory(role="admin")
    household = approved()
    listing = cast(Listing, ListingFactory(quantity_total=10, quantity_reserved=4))
    reservation = Reservation.objects.create(
        listing=listing,
        household=household,
        quantity=4,
        pickup_code="123456",
        status=ReservationStatus.RESERVED,
        late_cancel=True,
        made_by_type=MadeByType.HOUSEHOLD,
        made_by=cast(Any, admin),
    )

    assert post(admin, household, "suspend").status_code == 200
    reservation.refresh_from_db()
    listing.refresh_from_db()
    assert reservation.status == ReservationStatus.CANCELLED
    assert reservation.late_cancel is False
    assert listing.quantity_reserved == 0


@pytest.mark.parametrize(
    "role", [None, "beneficiary", "store_staff", "store_manager", "intake_worker"]
)
def test_every_non_admin_role_is_refused(role: str | None) -> None:
    store = StoreFactory() if role in ("store_staff", "store_manager") else None
    actor = UserFactory(role=role, store=store) if role else None
    response = post(actor, approved(), "suspend")
    assert response.status_code == (401 if actor is None else 403)


@pytest.mark.parametrize("action", ["suspend", "reactivate"])
def test_reason_is_required(action: str) -> None:
    household = approved(
        status=(
            Household.Status.SUSPENDED
            if action == "reactivate"
            else Household.Status.APPROVED
        )
    )
    response = post(UserFactory(role="admin"), household, action, "   ")
    assert response.status_code == 400
    assert "reason" in response.data["fields"]


def test_reactivation_refuses_expired_file() -> None:
    household = approved(
        status=Household.Status.SUSPENDED,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    response = post(UserFactory(role="admin"), household, "reactivate")
    assert response.status_code == 400
    household.refresh_from_db()
    assert household.status == Household.Status.SUSPENDED


def test_repeated_and_unknown_transitions_are_refused() -> None:
    admin = UserFactory(role="admin")
    household = approved()
    assert post(admin, household, "reactivate").status_code == 400
    assert post(admin, household, "suspend").status_code == 200
    assert post(admin, household, "suspend").status_code == 400


def test_anonymized_household_is_hidden() -> None:
    household = approved(anonymized_at=timezone.now())
    assert post(UserFactory(role="admin"), household, "suspend").status_code == 404


def test_counter_only_household_can_be_suspended() -> None:
    household = approved(email=None)
    assert post(UserFactory(role="admin"), household, "suspend").status_code == 200


@pytest.mark.parametrize(
    ("action", "status", "subject"),
    [
        ("suspend", Household.Status.APPROVED, "suspended"),
        ("reactivate", Household.Status.SUSPENDED, "reactivated"),
    ],
)
def test_holder_is_emailed_after_commit(
    action: str,
    status: str,
    subject: str,
    django_capture_on_commit_callbacks: Any,
) -> None:
    household = approved(status=status)
    with django_capture_on_commit_callbacks(execute=True):
        assert post(UserFactory(role="admin"), household, action).status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["holder@example.test"]
    assert subject in mail.outbox[0].subject
