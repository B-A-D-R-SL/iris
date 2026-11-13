# AI contribution: 50% or more AI-generated
"""Recover committed approvals without reusing lost or expired bearer tokens."""

from hashlib import sha256
from io import StringIO
from typing import Any
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone

from adapters.mailer.base import MailerError
from adapters.mailer.fake import get_fake_mailer
from modules.accounts import services as account_services
from modules.accounts.models import Invitation, User
from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.notifications.models import EmailLog
from modules.notifications.tasks import DeliveryFailure, send_email
from modules.stores import services
from modules.stores.models import ApplicationStatus, Store
from modules.stores.tests.factories import PartnerApplicationFactory

DIRECT_CONTEXT: Any = None
pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures(
        "notification_rules", "partner_origin", "queued_partner_emails"
    ),
]


@pytest.mark.usefixtures("invitation_rule")
@pytest.mark.parametrize("recovery_fails", [False, True])
# rule: BR-PARTNER-05
def test_approval_email_failure_is_recoverable_with_a_fresh_link(
    admin,
    django_capture_on_commit_callbacks,
    queued_partner_emails,
    partner_events,
    recovery_fails,
):
    """Recovery replaces the bearer token without duplicating approval or audit."""
    application = PartnerApplicationFactory(language="en")
    with django_capture_on_commit_callbacks(execute=True):
        services.approve_application(application, admin)
    previous = Invitation.objects.get(email=application.contact_email)
    previous_hash = previous.token_hash
    mailer = get_fake_mailer()
    mailer.error = MailerError("transport_unavailable")
    with pytest.raises(DeliveryFailure):
        send_email(DIRECT_CONTEXT, **queued_partner_emails[0])
    failed_log = EmailLog.objects.get(pk=queued_partner_emails[0]["email_log_id"])
    assert failed_log.error == "transport_unavailable"
    assert failed_log.status == EmailLog.Status.RETRYING
    assert any(
        getattr(r, "event", None) == "email_retry_scheduled"
        for r in partner_events.records
    )
    records = str([vars(record) for record in partner_events.records])
    assert application.contact_email not in records and previous_hash not in records

    if recovery_fails:
        with django_capture_on_commit_callbacks(execute=True):
            services.resend_approval_invitation(application, admin)
        with pytest.raises(DeliveryFailure):
            send_email(DIRECT_CONTEXT, **queued_partner_emails[-1])
    mailer.error = None
    with django_capture_on_commit_callbacks(execute=True):
        services.resend_approval_invitation(application, admin)
        assert mailer.sent == []
    send_email(DIRECT_CONTEXT, **queued_partner_emails[-1])
    previous.refresh_from_db()
    assert previous.expires_at <= timezone.now()
    [message] = mailer.sent
    token = message["text"].split("/invitation/")[1].split()[0]
    replacement = Invitation.objects.get(token_hash=sha256(token.encode()).hexdigest())
    assert replacement.token_hash != previous_hash
    account = account_services.accept_invitation(token, "GeneratedTestPassword!8374")
    assert account.role == User.Role.STORE_MANAGER and account.store == previous.store
    application.refresh_from_db()
    assert application.status == ApplicationStatus.APPROVED
    assert Store.objects.filter(application=application).count() == 1
    assert AuditEvent.objects.filter(target_id=str(application.pk)).count() == 1
    assert token not in str([vars(record) for record in partner_events.records])
    with pytest.raises(ValidationError) as caught:
        services.resend_approval_invitation(application, admin)
    assert caught.value.code == "invitation_not_pending"
    assert Invitation.objects.filter(store=previous.store).count() == (
        3 if recovery_fails else 2
    )


@pytest.mark.usefixtures("invitation_rule")
# rule: BR-PARTNER-05
def test_reissue_invalidates_old_token_and_outer_rollback_preserves_it(
    admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    """A rolled-back recovery must keep the original token and delivery history."""
    application = PartnerApplicationFactory(language="fr")
    with django_capture_on_commit_callbacks(execute=True):
        services.approve_application(application, admin)
    send_email(DIRECT_CONTEXT, **queued_partner_emails[0])
    mailer = get_fake_mailer()
    token = mailer.sent[0]["text"].split("/invitation/")[1].split()[0]
    previous = Invitation.objects.get(email=application.contact_email)
    expiry = previous.expires_at
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.resend_approval_invitation(application, admin)
        raise RuntimeError("recovery rolled back")
    previous.refresh_from_db()
    assert previous.expires_at == expiry
    assert Invitation.objects.filter(store=previous.store).count() == 1
    assert not callbacks and len(mailer.sent) == 1
    assert len(queued_partner_emails) == 1 and EmailLog.objects.count() == 1
    with django_capture_on_commit_callbacks(execute=True):
        services.resend_approval_invitation(application, admin)
    send_email(DIRECT_CONTEXT, **queued_partner_emails[1])
    with pytest.raises(ValidationError) as caught:
        account_services.accept_invitation(token, "GeneratedTestPassword!8374")
    assert caught.value.code == "invitation_expired"
    assert "Votre demande" in mailer.sent[1]["subject"]


@pytest.mark.usefixtures("invitation_rule")
# rule: BR-PARTNER-05
def test_failed_reissue_keeps_previous_invitation_and_sends_nothing(
    admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    application = PartnerApplicationFactory()
    with django_capture_on_commit_callbacks(execute=False):
        services.approve_application(application, admin)
    previous = Invitation.objects.get(email=application.contact_email)
    expiry = previous.expires_at
    with (
        patch("modules.accounts.services.rule_queries.active", return_value=None),
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(ValidationError),
    ):
        services.resend_approval_invitation(application, admin)
    previous.refresh_from_db()
    assert previous.expires_at == expiry
    assert Invitation.objects.filter(store=previous.store).count() == 1
    assert EmailLog.objects.count() == 1
    assert not callbacks and not queued_partner_emails and not get_fake_mailer().sent


@pytest.mark.usefixtures("invitation_rule")
# rule: BR-PARTNER-05
def test_recovery_command_requires_admin_and_never_prints_contact_or_token(
    admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    application = PartnerApplicationFactory()
    with django_capture_on_commit_callbacks(execute=False):
        services.approve_application(application, admin)
    output = StringIO()
    with django_capture_on_commit_callbacks(execute=True):
        call_command(
            "resend_partner_invitation",
            str(application.pk),
            admin_id=admin.pk,
            stdout=output,
        )
    assert str(application.pk) in output.getvalue()
    [job] = queued_partner_emails
    assert not get_fake_mailer().sent
    send_email(DIRECT_CONTEXT, **job)
    [message] = get_fake_mailer().sent
    token = message["text"].split("/invitation/")[1].split()[0]
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
def test_reissue_refuses_unapproved_applications(admin, status):
    application = PartnerApplicationFactory(status=status, decision_reason="reason")
    with pytest.raises(ValidationError, match="Only approved"):
        services.resend_approval_invitation(application, admin)
    assert not Invitation.objects.filter(email=application.contact_email).exists()


@pytest.mark.usefixtures("invitation_rule")
def test_reissue_refuses_existing_account_and_preserves_invitation(admin):
    application = PartnerApplicationFactory()
    services.approve_application(application, admin)
    previous = Invitation.objects.get(email=application.contact_email)
    expiry = previous.expires_at
    UserFactory(email=application.contact_email)
    with pytest.raises(ValidationError) as caught:
        services.resend_approval_invitation(application, admin)
    assert caught.value.code == "email_already_registered"
    previous.refresh_from_db()
    assert previous.expires_at == expiry


@pytest.mark.usefixtures("invitation_rule")
def test_recovery_before_initial_delivery_suppresses_the_obsolete_queued_link(
    admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    """Reissue may win the race before the initial worker job starts."""
    application = PartnerApplicationFactory(language="en")
    with django_capture_on_commit_callbacks(execute=True):
        services.approve_application(application, admin)
    with django_capture_on_commit_callbacks(execute=True):
        services.resend_approval_invitation(application, admin)
    initial, replacement = queued_partner_emails
    send_email(DIRECT_CONTEXT, **initial)
    obsolete = EmailLog.objects.get(pk=initial["email_log_id"])
    assert obsolete.status == EmailLog.Status.FAILED
    assert obsolete.error == "invitation_unavailable"
    assert obsolete.attempts == 0
    assert not get_fake_mailer().sent
    send_email(DIRECT_CONTEXT, **replacement)
    latest = EmailLog.objects.get(pk=replacement["email_log_id"])
    assert latest.status == EmailLog.Status.SENT and latest.attempts == 1
    [message] = get_fake_mailer().sent
    assert replacement["context"]["invitation_url"] in message["text"]
    assert initial["context"]["invitation_url"] not in message["text"]


@pytest.mark.parametrize(
    "origin", ["", None, "http://iris.example", "https://iris.example/path"]
)
@pytest.mark.usefixtures("invitation_rule")
def test_bad_email_origin_keeps_the_reissued_invitation(
    settings, admin, origin, django_capture_on_commit_callbacks, queued_partner_emails
):
    """A deployment email error cannot roll back successful invitation recovery."""
    application = PartnerApplicationFactory()
    with django_capture_on_commit_callbacks(execute=True):
        services.approve_application(application, admin)
    previous = Invitation.objects.get(email=application.contact_email)
    queued_partner_emails.clear()
    settings.PUBLIC_APP_ORIGIN = origin
    with django_capture_on_commit_callbacks(execute=True):
        services.resend_approval_invitation(application, admin)
    previous.refresh_from_db()
    assert previous.expires_at <= timezone.now()
    replacement = Invitation.objects.exclude(pk=previous.pk).get(store=previous.store)
    assert replacement.token_hash != previous.token_hash
    assert replacement.expires_at > timezone.now()
    application.refresh_from_db()
    assert application.status == ApplicationStatus.APPROVED
    assert Store.objects.filter(application=application).count() == 1
    assert AuditEvent.objects.filter(target_id=str(application.pk)).count() == 1
    log = EmailLog.objects.exclude(status=EmailLog.Status.PENDING).get()
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_configuration_invalid"
    assert log.attempts == 0 and log.sent_at is None
    assert not queued_partner_emails and not get_fake_mailer().sent
