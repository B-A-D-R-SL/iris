# AI contribution: 50% or more AI-generated
"""Recover committed approvals without reusing lost or expired bearer tokens."""

from hashlib import sha256
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from modules.accounts.models import Invitation, User
from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.stores import services
from modules.stores.models import ApplicationStatus, Store
from modules.stores.tests.factories import PartnerApplicationFactory
from modules.stores.tests.test_partner_application_service import RecordingMailer

pytestmark = pytest.mark.django_db


# Size/complexity exception: the same invitation must survive email loss, retry,
# reissue and acceptance to prove token continuity and absence of duplicate decisions.
@pytest.mark.usefixtures("invitation_rule")
@pytest.mark.parametrize("recovery_fails", [False, True])
# rule: BR-PARTNER-05
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
    failure = next(
        r
        for r in caplog.records
        if getattr(r, "event", None) == "partner_application_decision_email_failed"
    )
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
    with pytest.raises(ValidationError) as caught:
        services.resend_approval_invitation(application, admin, mailer=mailer)
    assert caught.value.code == "invitation_not_pending"
    assert Invitation.objects.filter(store=previous.store).count() == (
        3 if recovery_fails else 2
    )


@pytest.mark.usefixtures("invitation_rule")
# rule: BR-PARTNER-05
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
# rule: BR-PARTNER-05
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
# rule: BR-PARTNER-05
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
# rule: BR-PARTNER-05
def test_reissue_refuses_unapproved_applications(settings, admin, status):
    """Recovery cannot create a store or bypass the original approval decision."""
    settings.FRONTEND_URL = "https://iris.example"
    application = PartnerApplicationFactory(status=status, decision_reason="reason")
    with pytest.raises(ValidationError, match="Only approved"):
        services.resend_approval_invitation(application, admin)
    assert not Invitation.objects.filter(email=application.contact_email).exists()


@pytest.mark.usefixtures("invitation_rule")
# rule: BR-PARTNER-05
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
