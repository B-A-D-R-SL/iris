# AI contribution: 50% or more AI-generated
"""US-32 suspension transitions, reservation cancellation and authorization."""

from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
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
    """Build a status action URL."""
    return reverse(f"staff-households-{action}", kwargs={"id": household.pk})


def approved(**changes: Any) -> Household:
    """Create a valid approved household unless fields are overridden."""
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
    """Post one status action as the given actor."""
    client = APIClient()
    if actor is not None:
        client.force_authenticate(actor)
    return client.post(url(household, action), {"reason": reason}, format="json")


# rule: BR-HH-SUSPEND-001
def test_admin_suspends_and_reactivates_with_audits_br_hh_suspend_001() -> None:
    """An administrator can perform both audited transitions."""
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


# rule: BR-HH-SUSPEND-002
def test_suspending_cancels_open_reservations_and_returns_units_br_hh_suspend_002() -> (
    None
):
    """Suspension cancels reserved claims and releases their units."""
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
@pytest.mark.parametrize("action", ["suspend", "reactivate"])
# rule: BR-HH-SUSPEND-001
def test_every_non_admin_role_is_refused_br_hh_suspend_001(
    role: str | None, action: str
) -> None:
    """Every non-admin role is refused by both status endpoints."""
    store = StoreFactory() if role in ("store_staff", "store_manager") else None
    actor = UserFactory(role=role, store=store) if role else None
    status = (
        Household.Status.SUSPENDED
        if action == "reactivate"
        else Household.Status.APPROVED
    )
    response = post(actor, approved(status=status), action)
    assert response.status_code == (401 if actor is None else 403)


@pytest.mark.parametrize("action", ["suspend", "reactivate"])
def test_reason_is_required(action: str) -> None:
    """Both transitions require a non-blank reason."""
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


# rule: BR-HH-SUSPEND-002
def test_reactivation_refuses_expired_file_br_hh_suspend_002() -> None:
    """An expired suspended file cannot be reactivated."""
    household = approved(
        status=Household.Status.SUSPENDED,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    response = post(UserFactory(role="admin"), household, "reactivate")
    assert response.status_code == 400
    household.refresh_from_db()
    assert household.status == Household.Status.SUSPENDED


def test_repeated_and_unknown_transitions_are_refused() -> None:
    """Only the two defined source states may transition."""
    admin = UserFactory(role="admin")
    household = approved()
    assert post(admin, household, "reactivate").status_code == 400
    assert post(admin, household, "suspend").status_code == 200
    assert post(admin, household, "suspend").status_code == 400


@pytest.mark.parametrize("action", ["suspend", "reactivate"])
def test_anonymized_household_is_hidden(action: str) -> None:
    """Neither endpoint reveals an anonymized household."""
    status = (
        Household.Status.SUSPENDED
        if action == "reactivate"
        else Household.Status.APPROVED
    )
    household = approved(status=status, anonymized_at=timezone.now())
    assert post(UserFactory(role="admin"), household, action).status_code == 404


# rule: BR-HH-SUSPEND-003
def test_counter_only_household_can_be_suspended_br_hh_suspend_003() -> None:
    """A household without email still changes status."""
    household = approved(email=None)
    assert post(UserFactory(role="admin"), household, "suspend").status_code == 200


@pytest.mark.parametrize(
    ("action", "status", "subject"),
    [
        ("suspend", Household.Status.APPROVED, "suspended"),
        ("reactivate", Household.Status.SUSPENDED, "reactivated"),
    ],
)
def test_holder_is_emailed_after_commit_br_hh_suspend_003(
    action: str,
    status: str,
    subject: str,
    django_capture_on_commit_callbacks: Any,
) -> None:
    """A localized holder notice is sent after commit."""
    household = approved(status=status)
    with django_capture_on_commit_callbacks(execute=True):
        assert post(UserFactory(role="admin"), household, action).status_code == 200
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["holder@example.test"]
    assert subject in mail.outbox[0].subject


def test_email_failure_does_not_undo_change_br_hh_suspend_003(
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A delivery failure cannot undo committed status changes."""
    household = approved()

    def fail(*args: Any, **kwargs: Any) -> int:
        raise RuntimeError("mail unavailable")

    monkeypatch.setattr("adapters.mailer.smtp.SmtpMailer.send", fail)
    with django_capture_on_commit_callbacks(execute=True):
        assert post(UserFactory(role="admin"), household, "suspend").status_code == 200
    household.refresh_from_db()
    assert household.status == Household.Status.SUSPENDED
    record = next(
        item
        for item in caplog.records
        if item.message == "household_status_email_failed"
    )
    assert getattr(record, "event", None) == "household_status_email_failed"


def make_reservation(
    listing: Listing,
    household: Household,
    actor: Any,
    *,
    quantity: int,
    pickup_code: str,
    status: str,
) -> Reservation:
    """Create one reservation for suspension boundary tests."""
    return Reservation.objects.create(
        listing=listing,
        household=household,
        quantity=quantity,
        pickup_code=pickup_code,
        status=status,
        made_by_type=MadeByType.HOUSEHOLD,
        made_by=actor,
    )


# rule: BR-HH-SUSPEND-002
def test_suspension_leaves_closed_and_other_household_reservations_unchanged_br_hh_suspend_002() -> (
    None
):
    """Suspension changes only this household's reserved claims."""
    admin = UserFactory(role="admin")
    household = approved()
    other = approved(email="other@example.test")
    listing = cast(Listing, ListingFactory(quantity_total=10, quantity_reserved=5))
    reserved = make_reservation(
        listing,
        household,
        admin,
        quantity=2,
        pickup_code="100001",
        status=ReservationStatus.RESERVED,
    )
    picked_up = make_reservation(
        listing,
        household,
        admin,
        quantity=1,
        pickup_code="100002",
        status=ReservationStatus.PICKED_UP,
    )
    other_reserved = make_reservation(
        listing,
        other,
        admin,
        quantity=3,
        pickup_code="100003",
        status=ReservationStatus.RESERVED,
    )

    assert post(admin, household, "suspend").status_code == 200
    listing.refresh_from_db()
    reserved.refresh_from_db()
    picked_up.refresh_from_db()
    other_reserved.refresh_from_db()
    assert listing.quantity_reserved == 3
    assert reserved.status == ReservationStatus.CANCELLED
    assert picked_up.status == ReservationStatus.PICKED_UP
    assert other_reserved.status == ReservationStatus.RESERVED


def test_cancellation_failure_rolls_back_suspension_br_hh_suspend_002(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation failure rolls back the status and audit event."""
    household = approved()

    def fail(household_id: Any) -> int:
        """Simulate inconsistent reserved stock."""
        raise ValidationError({"quantity": "inconsistent reservation count"})

    monkeypatch.setattr(
        "modules.households.services.reservation_services.cancel_open_for_household",
        fail,
    )
    response = post(UserFactory(role="admin"), household, "suspend")
    assert response.status_code == 400
    household.refresh_from_db()
    assert household.status == Household.Status.APPROVED
    assert not AuditEvent.objects.filter(target_id=str(household.pk)).exists()


@pytest.mark.parametrize(
    ("channel", "status", "expected_actions"),
    [
        (Household.Channel.ONLINE, Household.Status.APPROVED, ["suspend"]),
        (Household.Channel.WALK_IN, Household.Status.SUSPENDED, ["reactivate"]),
    ],
)
def test_detail_get_reads_online_and_walk_in_households_br_hh_suspend_001(
    channel: str,
    status: str,
    expected_actions: list[str],
) -> None:
    """Staff can read both household channels and server-derived actions."""
    household = approved(
        channel=channel,
        status=status,
        created_by=None if channel == Household.Channel.ONLINE else UserFactory(),
    )
    client = APIClient()
    client.force_authenticate(UserFactory(role="admin"))
    response = client.get(
        reverse("staff-households-detail", kwargs={"id": household.pk})
    )
    assert response.status_code == 200
    assert response.data["id"] == str(household.pk)
    assert response.data["allowed_actions"] == expected_actions
    if channel == Household.Channel.ONLINE:
        assert response.data["created_by_email"] is None


def test_detail_get_hides_reactivation_for_expired_file_br_hh_suspend_002() -> None:
    """The detail response hides reactivation when expiry has passed."""
    household = approved(
        status=Household.Status.SUSPENDED,
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    client = APIClient()
    client.force_authenticate(UserFactory(role="admin"))
    response = client.get(
        reverse("staff-households-detail", kwargs={"id": household.pk})
    )
    assert response.status_code == 200
    assert response.data["allowed_actions"] == []


@pytest.mark.parametrize(
    "reason",
    [
        "SIN 123 456 789",
        "Income $45000",
        "Immigration status refugee",
        "Passport document text",
    ],
)
# rule: BR-HH-SUSPEND-001
def test_sensitive_reason_is_refused_before_audit_or_email(reason: str) -> None:
    """Sensitive reason text never reaches audit records or notifications."""
    household = approved()
    response = post(UserFactory(role="admin"), household, "suspend", reason)
    assert response.status_code == 400
    assert "reason" in response.data["fields"]
    household.refresh_from_db()
    assert household.status == Household.Status.APPROVED
    assert not AuditEvent.objects.filter(target_id=str(household.pk)).exists()
    assert mail.outbox == []
