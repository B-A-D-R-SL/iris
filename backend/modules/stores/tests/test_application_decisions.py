# AI contribution: 50% or more AI-generated
"""Partner decisions preserve consistency and notify only after commit."""

from datetime import timedelta
from hashlib import sha256
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from modules.accounts.models import Invitation, User
from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.rules.models import RuleSetVersion
from modules.stores import services
from modules.stores.models import ApplicationStatus, Store
from modules.stores.tests.factories import PartnerApplicationFactory
from modules.stores.tests.test_partner_application_service import RecordingMailer

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return UserFactory(role=User.Role.ADMIN)


@pytest.fixture
def invitation_rule(admin):
    return RuleSetVersion.objects.create(
        rule_type="invitations",
        version=1,
        values={"expires_after_days": 7},
        effective_from=timezone.now() - timedelta(days=1),
        created_by=admin,
    )


@pytest.mark.usefixtures("invitation_rule")
def test_approval_creates_store_invitation_and_audit_after_commit(
    settings, admin, django_capture_on_commit_callbacks
):
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory(language="en")
    mailer = RecordingMailer()
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        result = services.approve_application(application, admin, mailer=mailer)
        assert mailer.sent == []
    assert result.status == ApplicationStatus.APPROVED
    assert result.decided_by == admin and result.decided_at is not None
    store = Store.objects.get(application=application)
    assert store.name == application.business_name
    assert store.opening_hours == {"notes": application.opening_hours}
    invitation = Invitation.objects.get(store=store)
    assert invitation.role == User.Role.STORE_MANAGER
    assert invitation.email == application.contact_email
    assert invitation.invited_by == admin
    event = AuditEvent.objects.get(target_id=str(application.pk))
    assert event.actor == admin and event.metadata == {"outcome": "approved"}
    for callback in callbacks:
        callback()
    message = mailer.sent[0]
    assert message["to"] == [application.contact_email]
    token = message["text"].split("https://iris.example/invitation/")[1].split()[0]
    assert sha256(token.encode()).hexdigest() == invitation.token_hash
    with pytest.raises(services.ApplicationAlreadyDecided):
        services.approve_application(application, admin, mailer=mailer)
    assert Store.objects.filter(application=application).count() == 1
    assert Invitation.objects.filter(store=store).count() == 1


def test_rejection_requires_reason_and_sends_after_commit(
    admin, django_capture_on_commit_callbacks
):
    application = PartnerApplicationFactory(language="fr")
    mailer = RecordingMailer()
    for reason in ("", "  ", "x" * 501):
        with pytest.raises(ValidationError):
            services.reject_application(application, admin, reason, mailer=mailer)
    with django_capture_on_commit_callbacks(execute=True):
        result = services.reject_application(
            application, admin, "  Motif  ", mailer=mailer
        )
        assert not mailer.sent
    assert result.status == ApplicationStatus.REJECTED
    assert result.decision_reason == "Motif" and result.decided_by == admin
    assert AuditEvent.objects.get(target_id=str(application.pk)).metadata == {
        "outcome": "rejected"
    }
    assert "Motif" in mailer.sent[0]["text"]
    with pytest.raises(services.ApplicationAlreadyDecided):
        services.reject_application(application, admin, "again")


@pytest.mark.parametrize(
    "role,active", [(User.Role.BENEFICIARY, True), (User.Role.ADMIN, False)]
)
def test_decision_requires_active_admin(role, active):
    application = PartnerApplicationFactory()
    user = UserFactory(role=role, is_active=active)
    with pytest.raises(PermissionDenied):
        services.reject_application(application, user, "reason")
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED


@pytest.mark.usefixtures("invitation_rule")
def test_approval_rolls_back_all_changes_if_audit_fails(
    settings, admin, django_capture_on_commit_callbacks
):
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory()
    mailer = RecordingMailer()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        patch("modules.audit.services.record", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        services.approve_application(application, admin, mailer=mailer)
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()
    assert not Invitation.objects.filter(email=application.contact_email).exists()
    assert not callbacks and not mailer.sent


@pytest.mark.usefixtures("invitation_rule")
def test_outer_rollback_cancels_decision_email(
    settings, admin, django_capture_on_commit_callbacks
):
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory()
    mailer = RecordingMailer()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.approve_application(application, admin, mailer=mailer)
        raise RuntimeError
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not callbacks and not mailer.sent


def test_stale_application_cannot_be_approved_after_rejection(settings, admin):
    settings.FRONTEND_URL = "https://iris.example"
    stale = PartnerApplicationFactory()
    services.reject_application(stale, admin, "Not eligible", mailer=RecordingMailer())
    with pytest.raises(services.ApplicationAlreadyDecided):
        services.approve_application(stale, admin, mailer=RecordingMailer())
    assert not Store.objects.filter(application=stale).exists()


def test_invitation_failure_rolls_back_store_and_decision(settings, admin):
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory()
    with (
        patch(
            "modules.accounts.services.create_invitation",
            side_effect=ValidationError("unavailable"),
        ),
        pytest.raises(ValidationError),
    ):
        services.approve_application(application, admin, mailer=RecordingMailer())
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()
    assert not AuditEvent.objects.filter(target_id=str(application.pk)).exists()
