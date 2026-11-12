# AI contribution: 50% or more AI-generated
"""Partner decisions preserve consistency and notify only after commit."""

from datetime import timedelta
from hashlib import sha256
from unittest.mock import patch

import pytest
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
    ValidationError,
)
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


@pytest.mark.parametrize(
    "role",
    [
        User.Role.BENEFICIARY,
        User.Role.INTAKE_WORKER,
        User.Role.STORE_MANAGER,
        User.Role.STORE_STAFF,
    ],
)
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_each_non_admin_role_cannot_decide(role, decision, settings):
    from modules.stores.tests.factories import StoreFactory

    settings.FRONTEND_URL = "https://iris.example"
    user = UserFactory(
        role=role,
        store=StoreFactory()
        if role in (User.Role.STORE_MANAGER, User.Role.STORE_STAFF)
        else None,
    )
    application = PartnerApplicationFactory()
    with pytest.raises(PermissionDenied):
        if decision == "approve":
            services.approve_application(application, user, mailer=RecordingMailer())
        else:
            services.reject_application(
                application, user, "reason", mailer=RecordingMailer()
            )
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()
    assert not AuditEvent.objects.filter(target_id=str(application.pk)).exists()


def test_rejection_accepts_maximum_length_reason(
    admin, django_capture_on_commit_callbacks
):
    application = PartnerApplicationFactory(language="en")
    mailer = RecordingMailer()
    with django_capture_on_commit_callbacks(execute=True):
        services.reject_application(application, admin, "x" * 500, mailer=mailer)
    application.refresh_from_db()
    assert application.decision_reason == "x" * 500
    assert mailer.sent[0]["to"] == [application.contact_email]
    assert "x" * 500 in mailer.sent[0]["text"]


def test_mail_failure_preserves_decision_without_logging_personal_data(
    admin, django_capture_on_commit_callbacks, caplog
):
    from modules.stores.tests.test_partner_application_service import FailingMailer

    application = PartnerApplicationFactory(
        language="en", contact_email="owner@example.test"
    )
    with django_capture_on_commit_callbacks(execute=True):
        services.reject_application(
            application, admin, "reason", mailer=FailingMailer()
        )
    application.refresh_from_db()
    assert application.status == ApplicationStatus.REJECTED
    assert AuditEvent.objects.filter(target_id=str(application.pk)).exists()
    assert "partner_application_decision_email_failed" in caplog.text
    assert application.contact_email not in caplog.text


def test_rejection_audit_failure_rolls_back_and_sends_no_email(
    admin, django_capture_on_commit_callbacks
):
    application = PartnerApplicationFactory()
    mailer = RecordingMailer()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        patch("modules.audit.services.record", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        services.reject_application(application, admin, "reason", mailer=mailer)
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert application.decision_reason is None
    assert not callbacks and not mailer.sent


@pytest.mark.parametrize(
    "origin",
    [
        "",
        "invalid",
        "ftp://iris.example",
        "https://iris.example/path",
        "https://iris.example?query=1",
        "https://iris.example?",
        "https://iris.example#",
        "https://user:pass@iris.example",
        None,
    ],
)
def test_bad_frontend_configuration_fails_before_application_lock(
    settings, admin, origin
):
    """Deployment errors are explicit and perform no application lookup or writes."""
    settings.FRONTEND_URL = origin
    application = PartnerApplicationFactory()
    with (
        patch("modules.stores.services._locked_application") as locked,
        pytest.raises(ImproperlyConfigured, match="FRONTEND_URL"),
    ):
        services.approve_application(application, admin)
    locked.assert_not_called()
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()


def test_approval_authorizes_before_reporting_bad_configuration(settings):
    """Configuration errors do not replace authorization failures."""
    settings.FRONTEND_URL = ""
    application = PartnerApplicationFactory()
    with pytest.raises(PermissionDenied):
        services.approve_application(
            application, UserFactory(role=User.Role.BENEFICIARY)
        )


@pytest.mark.usefixtures("invitation_rule")
@pytest.mark.parametrize("recovery_fails", [False, True])
def test_approval_email_failure_is_recoverable_with_a_fresh_link(
    settings, admin, django_capture_on_commit_callbacks, caplog, recovery_fails
):
    """Recovery expires the lost link without repeating the approval or audit."""
    import json

    from iris.observability import JsonLogFormatter
    from modules.accounts import services as account_services
    from modules.stores.tests.test_partner_application_service import FailingMailer

    settings.FRONTEND_URL = "https://iris.example/"
    application = PartnerApplicationFactory(language="en")
    with django_capture_on_commit_callbacks(execute=True):
        services.approve_application(application, admin, mailer=FailingMailer())
    previous = Invitation.objects.get(email=application.contact_email)
    previous_hash = previous.token_hash
    failure = next(r for r in caplog.records if r.name == "iris.stores")
    encoded = JsonLogFormatter().format(failure)
    assert json.loads(encoded)["application_id"] == str(application.pk)
    assert json.loads(encoded)["event"] == "partner_application_decision_email_failed"
    assert application.contact_email not in encoded and previous_hash not in encoded

    if recovery_fails:
        with django_capture_on_commit_callbacks(execute=True):
            services.resend_approval_invitation(
                application, admin, mailer=FailingMailer()
            )
    mailer = RecordingMailer()
    with django_capture_on_commit_callbacks(execute=True):
        services.resend_approval_invitation(application, admin, mailer=mailer)
        assert mailer.sent == []
    previous.refresh_from_db()
    assert previous.expires_at <= timezone.now()
    token = (
        mailer.sent[0]["text"].split("https://iris.example/invitation/")[1].split()[0]
    )
    replacement = Invitation.objects.get(token_hash=sha256(token.encode()).hexdigest())
    assert replacement.token_hash != previous_hash
    account = account_services.accept_invitation(token, "GeneratedTestPassword!8374")
    assert account.role == User.Role.STORE_MANAGER and account.store == previous.store
    application.refresh_from_db()
    assert application.status == ApplicationStatus.APPROVED
    assert Store.objects.filter(application=application).count() == 1
    assert AuditEvent.objects.filter(target_id=str(application.pk)).count() == 1
    assert token not in caplog.text
    with pytest.raises(ValidationError, match="No unaccepted"):
        services.resend_approval_invitation(application, admin, mailer=mailer)
    assert Invitation.objects.filter(store=previous.store).count() == (
        3 if recovery_fails else 2
    )


@pytest.mark.usefixtures("invitation_rule")
def test_reissue_invalidates_old_token_and_outer_rollback_preserves_it(
    settings, admin, django_capture_on_commit_callbacks
):
    """Old tokens expire on commit; a rolled-back recovery never invalidates them."""
    from modules.accounts import services as account_services

    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory(language="fr")
    mailer = RecordingMailer()
    with django_capture_on_commit_callbacks(execute=True):
        services.approve_application(application, admin, mailer=mailer)
    token = mailer.sent[0]["text"].split("/invitation/")[1].split()[0]
    previous = Invitation.objects.get(email=application.contact_email)
    expiry = previous.expires_at
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.resend_approval_invitation(application, admin, mailer=mailer)
        raise RuntimeError
    previous.refresh_from_db()
    assert previous.expires_at == expiry
    assert Invitation.objects.filter(store=previous.store).count() == 1
    assert not callbacks and len(mailer.sent) == 1
    with django_capture_on_commit_callbacks(execute=True):
        services.resend_approval_invitation(application, admin, mailer=mailer)
    with pytest.raises(ValidationError) as caught:
        account_services.accept_invitation(token, "GeneratedTestPassword!8374")
    assert caught.value.code == "invitation_expired"
    assert "Votre demande" in mailer.sent[1]["subject"]


@pytest.mark.usefixtures("invitation_rule")
def test_failed_reissue_keeps_previous_invitation_and_sends_nothing(
    settings, admin, django_capture_on_commit_callbacks
):
    """Unavailable issuance configuration rolls back expiry and email scheduling."""
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory()
    with django_capture_on_commit_callbacks(execute=False):
        services.approve_application(application, admin, mailer=RecordingMailer())
    previous = Invitation.objects.get(email=application.contact_email)
    expiry = previous.expires_at
    mailer = RecordingMailer()
    with (
        patch("modules.accounts.services.rule_queries.active", return_value=None),
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(ValidationError),
    ):
        services.resend_approval_invitation(application, admin, mailer=mailer)
    previous.refresh_from_db()
    assert previous.expires_at == expiry
    assert Invitation.objects.filter(store=previous.store).count() == 1
    assert not callbacks and not mailer.sent


@pytest.mark.usefixtures("invitation_rule")
def test_recovery_command_requires_admin_and_never_prints_contact_or_token(
    settings, admin, django_capture_on_commit_callbacks
):
    """Operators can reissue by UUID; non-admins cannot issue invitations."""
    from io import StringIO

    from django.core import mail
    from django.core.management import call_command
    from django.core.management.base import CommandError

    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory()
    with django_capture_on_commit_callbacks(execute=False):
        services.approve_application(application, admin, mailer=RecordingMailer())
    output = StringIO()
    with django_capture_on_commit_callbacks(execute=True):
        call_command(
            "resend_partner_invitation",
            str(application.pk),
            admin_id=admin.pk,
            stdout=output,
        )
    assert str(application.pk) in output.getvalue()
    assert len(mail.outbox) == 1
    token = mail.outbox[0].body.split("/invitation/")[1].split()[0]
    assert application.contact_email not in output.getvalue()
    assert token not in output.getvalue()
    for user in (
        UserFactory(role=User.Role.BENEFICIARY),
        UserFactory(role=User.Role.ADMIN, is_active=False),
    ):
        with pytest.raises(CommandError, match="active admin"):
            call_command(
                "resend_partner_invitation",
                str(application.pk),
                admin_id=user.pk,
                stdout=output,
            )
    assert Invitation.objects.filter(email=application.contact_email).count() == 2


@pytest.mark.parametrize(
    "status", [ApplicationStatus.SUBMITTED, ApplicationStatus.REJECTED]
)
def test_reissue_refuses_unapproved_applications(settings, admin, status):
    """Recovery cannot create a store or bypass the original approval decision."""
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory(status=status, decision_reason="reason")
    with pytest.raises(ValidationError, match="Only approved"):
        services.resend_approval_invitation(application, admin)
    assert not Invitation.objects.filter(email=application.contact_email).exists()


@pytest.mark.usefixtures("invitation_rule")
def test_reissue_refuses_existing_account_and_preserves_invitation(settings, admin):
    """Recovery cannot reset or replace an existing user's account."""
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory()
    services.approve_application(application, admin, mailer=RecordingMailer())
    previous = Invitation.objects.get(email=application.contact_email)
    expiry = previous.expires_at
    UserFactory(email=application.contact_email)
    with pytest.raises(ValidationError) as caught:
        services.resend_approval_invitation(application, admin)
    assert caught.value.code == "email_already_registered"
    previous.refresh_from_db()
    assert previous.expires_at == expiry
