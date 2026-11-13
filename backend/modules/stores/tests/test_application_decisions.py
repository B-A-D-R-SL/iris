# AI contribution: 50% or more AI-generated
"""Partner decisions preserve consistency and notify only after commit."""

from hashlib import sha256
from typing import Any
from unittest.mock import patch

import pytest
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
    ValidationError,
)
from django.db import transaction

from adapters.mailer.base import MailerError
from adapters.mailer.fake import get_fake_mailer
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
# Complexity exception: one lifecycle verifies the same persisted store/token/audit
# across commit and repeat refusal; assertions are observations, not input branches.
# rule: BR-PARTNER-03
def test_approval_creates_store_invitation_and_audit_after_commit(
    settings, admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    application = PartnerApplicationFactory(language="en")
    mailer = get_fake_mailer()
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        result = services.approve_application(application, admin)
        assert mailer.sent == []
        assert queued_partner_emails == []
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
    [job] = queued_partner_emails
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.template_key == "partner_application_approved"
    assert log.language == "en"
    assert not mailer.sent
    send_email(DIRECT_CONTEXT, **job)
    log.refresh_from_db()
    assert log.status == EmailLog.Status.SENT
    message = mailer.sent[0]
    assert message["to"] == [application.contact_email]
    token = message["text"].split("https://iris.example/invitation/")[1].split()[0]
    assert sha256(token.encode()).hexdigest() == invitation.token_hash
    with pytest.raises(services.ApplicationAlreadyDecided):
        services.approve_application(application, admin)
    assert Store.objects.filter(application=application).count() == 1
    assert Invitation.objects.filter(store=store).count() == 1


# rule: BR-PARTNER-04
def test_rejection_requires_reason_and_sends_after_commit(
    admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    application = PartnerApplicationFactory(language="fr")
    mailer = get_fake_mailer()
    for reason in ("", "  ", "x" * 501):
        with pytest.raises(ValidationError):
            services.reject_application(application, admin, reason)
    with django_capture_on_commit_callbacks(execute=True):
        result = services.reject_application(application, admin, "  Motif  ")
        assert not mailer.sent
        assert not queued_partner_emails
    assert result.status == ApplicationStatus.REJECTED
    assert result.decision_reason == "Motif" and result.decided_by == admin
    assert AuditEvent.objects.get(target_id=str(application.pk)).metadata == {
        "outcome": "rejected"
    }
    [job] = queued_partner_emails
    assert job["context"] == {"reason": "Motif"}
    send_email(DIRECT_CONTEXT, **job)
    assert "Motif" in mailer.sent[0]["text"]
    with pytest.raises(services.ApplicationAlreadyDecided):
        services.reject_application(application, admin, "again")


@pytest.mark.parametrize("role,active", [(User.Role.ADMIN, False)])
def test_decision_requires_active_admin(role, active):
    application = PartnerApplicationFactory()
    user = UserFactory(role=role, is_active=active)
    with pytest.raises(PermissionDenied):
        services.reject_application(application, user, "reason")
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED


@pytest.mark.usefixtures("invitation_rule")
def test_approval_rolls_back_all_changes_if_audit_fails(
    settings, admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    application = PartnerApplicationFactory()
    mailer = get_fake_mailer()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        patch("modules.audit.services.record", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        services.approve_application(application, admin)
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()
    assert not Invitation.objects.filter(email=application.contact_email).exists()
    assert not callbacks and not mailer.sent
    assert not queued_partner_emails and not EmailLog.objects.exists()


@pytest.mark.usefixtures("invitation_rule")
def test_outer_rollback_cancels_decision_email(
    settings, admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    application = PartnerApplicationFactory()
    mailer = get_fake_mailer()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.approve_application(application, admin)
        raise RuntimeError
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not callbacks and not mailer.sent
    assert not queued_partner_emails and not EmailLog.objects.exists()


def test_stale_application_cannot_be_approved_after_rejection(settings, admin):
    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    stale = PartnerApplicationFactory()
    services.reject_application(stale, admin, "Not eligible")
    with pytest.raises(services.ApplicationAlreadyDecided):
        services.approve_application(stale, admin)
    assert not Store.objects.filter(application=stale).exists()


def test_invitation_failure_rolls_back_store_and_decision(settings, admin):
    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    application = PartnerApplicationFactory()
    with (
        patch(
            "modules.accounts.services.create_invitation",
            side_effect=ValidationError("unavailable"),
        ),
        pytest.raises(ValidationError),
    ):
        services.approve_application(application, admin)
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
# rule: BR-PARTNER-03
def test_each_non_admin_role_cannot_decide(role, decision, settings):
    from modules.stores.tests.factories import StoreFactory

    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    user = UserFactory(
        role=role,
        store=StoreFactory()
        if role in (User.Role.STORE_MANAGER, User.Role.STORE_STAFF)
        else None,
    )
    application = PartnerApplicationFactory()
    with pytest.raises(PermissionDenied):
        if decision == "approve":
            services.approve_application(application, user)
        else:
            services.reject_application(application, user, "reason")
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()
    assert not AuditEvent.objects.filter(target_id=str(application.pk)).exists()


def test_rejection_accepts_maximum_length_reason(
    admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    application = PartnerApplicationFactory(language="en")
    mailer = get_fake_mailer()
    with django_capture_on_commit_callbacks(execute=True):
        services.reject_application(application, admin, "x" * 500)
    application.refresh_from_db()
    assert application.decision_reason == "x" * 500
    [job] = queued_partner_emails
    send_email(DIRECT_CONTEXT, **job)
    assert mailer.sent[0]["to"] == [application.contact_email]
    assert "x" * 500 in mailer.sent[0]["text"]


def test_mail_failure_preserves_decision_without_logging_personal_data(
    admin, django_capture_on_commit_callbacks, queued_partner_emails, partner_events
):

    application = PartnerApplicationFactory(
        language="en", contact_email="owner@example.test"
    )
    with django_capture_on_commit_callbacks(execute=True):
        services.reject_application(application, admin, "reason")
    get_fake_mailer().error = MailerError("transport_unavailable")
    [job] = queued_partner_emails
    with pytest.raises(DeliveryFailure, match="^transport_unavailable$"):
        send_email(DIRECT_CONTEXT, **job)
    application.refresh_from_db()
    assert application.status == ApplicationStatus.REJECTED
    assert AuditEvent.objects.filter(target_id=str(application.pk)).exists()
    assert "email_retry_scheduled" in partner_events.text
    assert application.contact_email not in str(
        [vars(r) for r in partner_events.records]
    )
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.error == "transport_unavailable"


def test_rejection_audit_failure_rolls_back_and_sends_no_email(
    admin, django_capture_on_commit_callbacks, queued_partner_emails
):
    application = PartnerApplicationFactory()
    mailer = get_fake_mailer()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        patch("modules.audit.services.record", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        services.reject_application(application, admin, "reason")
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert application.decision_reason is None
    assert not callbacks and not mailer.sent
    assert not queued_partner_emails and not EmailLog.objects.exists()


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
    settings.PUBLIC_APP_ORIGIN = origin
    application = PartnerApplicationFactory()
    with (
        patch("modules.stores.services._locked_application") as locked,
        pytest.raises(ImproperlyConfigured, match="PUBLIC_APP_ORIGIN"),
    ):
        services.approve_application(application, admin)
    locked.assert_not_called()
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()


def test_approval_authorizes_before_reporting_bad_configuration(settings):
    """Configuration errors do not replace authorization failures."""
    settings.PUBLIC_APP_ORIGIN = ""
    application = PartnerApplicationFactory()
    with pytest.raises(PermissionDenied):
        services.approve_application(
            application, UserFactory(role=User.Role.BENEFICIARY)
        )


@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.usefixtures("invitation_rule")
def test_decision_logs_only_after_commit(
    settings, admin, django_capture_on_commit_callbacks, partner_events, decision
):
    """Committed outcomes are observable without logging contact data or rollback events."""
    settings.PUBLIC_APP_ORIGIN = "https://iris.example"
    application = PartnerApplicationFactory()
    with django_capture_on_commit_callbacks(execute=True):
        if decision == "approve":
            services.approve_application(application, admin)
        else:
            services.reject_application(application, admin, "reason")
        assert not [r for r in partner_events.records if r.name == "iris.stores"]
    events = [r.event for r in partner_events.records if r.name == "iris.stores"]
    assert events == [
        f"partner_application_{'approved' if decision == 'approve' else 'rejected'}"
    ]
    assert application.contact_email not in partner_events.text


@pytest.mark.parametrize(
    "origin",
    ["http://iris.example", "http://localhost.evil.example", "http://192.168.1.2"],
)
def test_plaintext_remote_invitation_origin_is_refused(settings, admin, origin):
    """Invitation bearer tokens are never issued over plaintext remote origins."""
    settings.PUBLIC_APP_ORIGIN = origin
    with pytest.raises(ImproperlyConfigured, match="HTTPS"):
        services.approve_application(PartnerApplicationFactory(), admin)


@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "http://127.0.0.1:5174", "http://[::1]:5173"]
)
@pytest.mark.usefixtures("invitation_rule")
def test_loopback_development_invitation_origin_is_allowed(settings, admin, origin):
    """Local development keeps working without a TLS proxy."""
    settings.PUBLIC_APP_ORIGIN = origin
    application = services.approve_application(PartnerApplicationFactory(), admin)
    assert application.status == ApplicationStatus.APPROVED


@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.usefixtures("invitation_rule")
def test_enqueue_failure_preserves_the_committed_decision_and_audit(
    admin, decision, monkeypatch, django_capture_on_commit_callbacks
):
    def unavailable(**kwargs):
        raise ConnectionError("private queue diagnostics")

    monkeypatch.setattr(send_email, "defer", unavailable)
    application = PartnerApplicationFactory()
    with django_capture_on_commit_callbacks(execute=True):
        if decision == "approve":
            services.approve_application(application, admin)
        else:
            services.reject_application(application, admin, "Decision reason")
    application.refresh_from_db()
    assert application.status == (
        ApplicationStatus.APPROVED
        if decision == "approve"
        else ApplicationStatus.REJECTED
    )
    assert AuditEvent.objects.filter(target_id=str(application.pk)).count() == 1
    log = EmailLog.objects.get(to_email=application.contact_email)
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "queue_unavailable"
    assert log.attempts == 0
    assert not get_fake_mailer().sent
    if decision == "approve":
        assert Store.objects.filter(application=application).count() == 1
        assert Invitation.objects.filter(email=application.contact_email).count() == 1


def test_rejection_reason_is_in_email_but_escaped_in_html_and_absent_from_logs(
    admin, django_capture_on_commit_callbacks, queued_partner_emails, partner_events
):
    reason = 'Generated <script>alert("example")</script> & reason'
    application = PartnerApplicationFactory(language="fr")
    with django_capture_on_commit_callbacks(execute=True):
        services.reject_application(application, admin, reason)
    [job] = queued_partner_emails
    assert job["context"] == {"reason": reason}
    send_email(DIRECT_CONTEXT, **job)
    [message] = get_fake_mailer().sent
    assert reason in message["text"]
    assert "<script>" not in message["html"]
    assert "&lt;script&gt;" in message["html"] and "&amp; reason" in message["html"]
    assert reason not in str([vars(record) for record in partner_events.records])
    assert reason not in message["subject"]
    application.refresh_from_db()
    assert application.decision_reason == reason
