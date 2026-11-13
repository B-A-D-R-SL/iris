# AI contribution: 50% or more AI-generated
"""Admin review API for partner applications (US-13, T-02.13.3).

The decision services have their own tests (test_application_decisions.py);
these check access, the HTTP contract and that a decision reaches the database.
"""

from datetime import timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from adapters.mailer.fake import get_fake_mailer
from modules.accounts.models import Invitation, User
from modules.accounts.tests.factories import UserFactory
from modules.audit.models import AuditEvent
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email
from modules.rules.models import RuleSetVersion
from modules.stores.models import ApplicationStatus, PartnerApplication, Store
from modules.stores.tests.factories import PartnerApplicationFactory, StoreFactory

DIRECT_CONTEXT: Any = None
pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures(
        "notification_rules", "partner_origin", "queued_partner_emails"
    ),
]

LIST_URL = "/api/staff/partner-applications/"
NON_ADMIN_ROLES = [
    User.Role.BENEFICIARY,
    User.Role.STORE_STAFF,
    User.Role.STORE_MANAGER,
    User.Role.INTAKE_WORKER,
]


def approve_url(application_id: object) -> str:
    """Approve route for one application."""
    return f"{LIST_URL}{application_id}/approve/"


def reject_url(application_id: object) -> str:
    """Reject route for one application."""
    return f"{LIST_URL}{application_id}/reject/"


@pytest.fixture
def admin() -> User:
    """An active admin account."""
    return cast(User, UserFactory(role=User.Role.ADMIN))


@pytest.fixture
def admin_client(admin: User) -> APIClient:
    """A client signed in as the admin."""
    client = APIClient()
    client.force_login(admin)
    return client


@pytest.fixture
def invitation_rule(admin: User) -> RuleSetVersion:
    """The invitation lifetime rule the approval service reads."""
    rule: RuleSetVersion = RuleSetVersion.objects.create(
        rule_type="invitations",
        version=1,
        values={"expires_after_days": 7},
        effective_from=timezone.now() - timedelta(days=1),
        created_by=admin,
    )
    return rule


def _application(**values: Any) -> PartnerApplication:
    """A saved application with generated data (typed for mypy)."""
    return cast(PartnerApplication, PartnerApplicationFactory(**values))


def _signed_in(role: str) -> APIClient:
    """A client signed in with the role; store roles get a store."""
    store = (
        StoreFactory()
        if role in (User.Role.STORE_STAFF, User.Role.STORE_MANAGER)
        else None
    )
    client = APIClient()
    client.force_login(UserFactory(role=role, store=store))
    return client


def _decided(status: str, reason: str | None = None) -> PartnerApplication:
    """An application already approved or rejected."""
    return _application(
        status=status, decision_reason=reason, decided_at=timezone.now()
    )


# Access -----------------------------------------------------------------


@pytest.mark.parametrize("role", NON_ADMIN_ROLES)
def test_non_admins_get_403_on_every_review_endpoint(role: str) -> None:
    """Every other role is refused and nothing changes."""
    application = _application()
    client = _signed_in(role)

    responses = [
        client.get(LIST_URL),
        client.post(approve_url(application.pk), {}, format="json"),
        client.post(reject_url(application.pk), {"reason": "No"}, format="json"),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403]
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()


def test_anonymous_visitors_are_refused() -> None:
    """Without a session the endpoints answer 401 (session challenge)."""
    application = _application()
    client = APIClient()

    assert client.get(LIST_URL).status_code == 401
    assert client.post(approve_url(application.pk)).status_code == 401
    assert client.post(reject_url(application.pk)).status_code == 401
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED


def test_an_inactive_admin_is_refused() -> None:
    """A deactivated admin account cannot review."""
    client = APIClient()
    client.force_authenticate(UserFactory(role=User.Role.ADMIN, is_active=False))

    assert client.get(LIST_URL).status_code == 403


def test_refusals_use_the_error_envelope() -> None:
    """403 bodies follow the team format {code, message, fields}."""
    response = _signed_in(User.Role.INTAKE_WORKER).get(LIST_URL)

    assert set(response.json()) == {"code", "message", "fields"}


# List -------------------------------------------------------------------


def test_list_is_oldest_first_and_filters_by_status(admin_client: APIClient) -> None:
    """Applications come oldest first; ?status= keeps one status."""
    newer = _application()
    older = _application()
    rejected = _decided(ApplicationStatus.REJECTED, reason="Outside the area")
    PartnerApplication.objects.filter(pk=older.pk).update(
        created_at=timezone.now() - timedelta(days=3)
    )
    PartnerApplication.objects.filter(pk=newer.pk).update(
        created_at=timezone.now() - timedelta(days=1)
    )

    everything = admin_client.get(LIST_URL).json()
    submitted = admin_client.get(LIST_URL, {"status": "submitted"}).json()

    assert everything["count"] == 3
    assert [item["id"] for item in submitted["results"]] == [
        str(older.pk),
        str(newer.pk),
    ]
    assert str(rejected.pk) not in {item["id"] for item in submitted["results"]}


def test_list_shows_what_the_admin_needs_to_decide(admin_client: APIClient) -> None:
    """Each item carries the business, the contact and the decision fields."""
    application = _application(message="We bake daily.")

    item = admin_client.get(LIST_URL).json()["results"][0]

    assert item["business_name"] == application.business_name
    assert item["contact_email"] == application.contact_email
    assert item["goods_categories"] == ["bakery"]
    assert item["message"] == "We bake daily."
    assert item["status"] == "submitted"
    assert item["can_decide"] is True
    assert item["decision_reason"] is None
    assert item["decided_at"] is None
    assert item["created_at"].endswith("Z")


def test_list_is_paginated(admin_client: APIClient) -> None:
    """Team paging convention: page_size, count, next."""
    for _ in range(3):
        _application()

    page = admin_client.get(LIST_URL, {"page_size": 2}).json()

    assert page["count"] == 3
    assert len(page["results"]) == 2
    assert page["next"]


def test_unknown_status_filter_is_a_validation_error(admin_client: APIClient) -> None:
    """An unknown status answers 400 with the field named."""
    response = admin_client.get(LIST_URL, {"status": "pending"})

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "status" in response.json()["fields"]


# Approve ----------------------------------------------------------------


@pytest.mark.usefixtures("invitation_rule", "partner_origin")
# rule: BR-PARTNER-03
def test_approve_creates_store_invitation_audit_and_email(
    admin: User,
    admin_client: APIClient,
    django_capture_on_commit_callbacks,
    queued_partner_emails,
) -> None:
    """Approval reaches the database and emails the contact after commit."""
    application = _application(language="en")

    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(approve_url(application.pk))
        assert not queued_partner_emails and not get_fake_mailer().sent

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert response.json()["can_decide"] is False
    store = Store.objects.get(application=application)
    invitation = Invitation.objects.get(store=store)
    assert invitation.role == User.Role.STORE_MANAGER
    assert invitation.email == application.contact_email
    assert AuditEvent.objects.filter(
        actor=admin, target_id=str(application.pk), metadata={"outcome": "approved"}
    ).exists()
    [job] = queued_partner_emails
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.template_key == "partner_application_approved" and log.language == "en"
    assert not get_fake_mailer().sent
    send_email(DIRECT_CONTEXT, **job)
    [message] = get_fake_mailer().sent
    assert message["to"] == [application.contact_email]
    assert "https://iris.example/invitation/" in message["text"]
    log.refresh_from_db()
    assert log.status == EmailLog.Status.SENT


@pytest.mark.usefixtures("partner_origin")
def test_missing_invitation_rule_rolls_back_approval(
    admin_client: APIClient, django_capture_on_commit_callbacks, queued_partner_emails
) -> None:
    """A failing invitation dependency answers 400 and leaves no partial approval."""
    application = _application()
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        response = admin_client.post(approve_url(application.pk))
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "non_field_errors" in response.json()["fields"]
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert application.decided_by is None and application.decided_at is None
    assert not Store.objects.filter(application=application).exists()
    assert not Invitation.objects.filter(email=application.contact_email).exists()
    assert not AuditEvent.objects.filter(target_id=str(application.pk)).exists()
    assert not callbacks and not get_fake_mailer().sent and not queued_partner_emails
    assert not EmailLog.objects.exists()


@pytest.mark.usefixtures("partner_origin")
@pytest.mark.parametrize(
    "language,message",
    [
        ("en", "An account already uses this email address."),
        ("fr", "Un compte utilise déjà ce courriel."),
    ],
)
def test_registered_contact_email_returns_a_localized_explanation(
    admin_client: APIClient, language: str, message: str
) -> None:
    """The UI receives the real refusal reason and approval remains uncommitted."""
    application = _application()
    UserFactory(email=application.contact_email)
    response = admin_client.post(
        approve_url(application.pk), HTTP_ACCEPT_LANGUAGE=language
    )
    assert response.status_code == 400
    assert response.json()["fields"]["non_field_errors"] == [message]
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert not Store.objects.filter(application=application).exists()
    assert not Invitation.objects.filter(email=application.contact_email).exists()
    assert not AuditEvent.objects.filter(target_id=str(application.pk)).exists()


@pytest.mark.usefixtures("partner_origin")
def test_approving_twice_answers_409(admin_client: APIClient) -> None:
    """A decided application cannot be decided again."""
    application = _decided(ApplicationStatus.APPROVED)

    response = admin_client.post(approve_url(application.pk))

    assert response.status_code == 409
    assert response.json()["code"] == "application_already_decided"


def test_unknown_application_answers_404(admin_client: APIClient) -> None:
    """A missing ID answers 404 for both decisions."""
    assert admin_client.post(approve_url(uuid4())).status_code == 404
    response = admin_client.post(reject_url(uuid4()), {"reason": "No"}, format="json")
    assert response.status_code == 404


@pytest.mark.usefixtures("invitation_rule")
def test_approval_succeeds_when_email_origin_is_unavailable(
    settings,
    admin_client: APIClient,
    django_capture_on_commit_callbacks,
    queued_partner_emails,
) -> None:
    """An email configuration problem is a delivery outcome, not an HTTP 500."""
    settings.PUBLIC_APP_ORIGIN = None
    application = _application()
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(approve_url(application.pk))
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    application.refresh_from_db()
    assert application.status == ApplicationStatus.APPROVED
    store = Store.objects.get(application=application)
    assert Invitation.objects.filter(store=store).count() == 1
    assert AuditEvent.objects.filter(target_id=str(application.pk)).count() == 1
    log = EmailLog.objects.get(template_key="partner_application_approved")
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_configuration_invalid" and log.attempts == 0
    assert not queued_partner_emails and not get_fake_mailer().sent


# Reject -----------------------------------------------------------------


def test_legacy_invalid_recipient_does_not_roll_back_rejection(
    admin_client: APIClient, django_capture_on_commit_callbacks, queued_partner_emails
) -> None:
    """An old persisted contact can be rejected even when email cannot address it."""
    application = _application(contact_email="legacy-invalid-recipient")
    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(
            reject_url(application.pk), {"reason": "Outside our area"}, format="json"
        )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    application.refresh_from_db()
    assert application.status == ApplicationStatus.REJECTED
    assert application.decision_reason == "Outside our area"
    assert AuditEvent.objects.get(target_id=str(application.pk)).metadata == {
        "outcome": "rejected"
    }
    log = EmailLog.objects.get(template_key="partner_application_rejected")
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_recipient_invalid" and log.attempts == 0
    assert not queued_partner_emails and not get_fake_mailer().sent


# rule: BR-PARTNER-04
def test_reject_records_reason_audit_and_email(
    admin: User,
    admin_client: APIClient,
    django_capture_on_commit_callbacks,
    queued_partner_emails,
) -> None:
    """Rejection saves the trimmed reason and emails it after commit."""
    application = _application(language="fr")

    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.post(
            reject_url(application.pk),
            {"reason": "  Hors de notre territoire  "},
            format="json",
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["can_decide"] is False
    assert body["decision_reason"] == "Hors de notre territoire"
    assert body["decided_at"]
    assert AuditEvent.objects.filter(
        actor=admin, target_id=str(application.pk), metadata={"outcome": "rejected"}
    ).exists()
    [job] = queued_partner_emails
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.template_key == "partner_application_rejected" and log.language == "fr"
    assert not get_fake_mailer().sent
    send_email(DIRECT_CONTEXT, **job)
    [message] = get_fake_mailer().sent
    assert "Hors de notre territoire" in message["text"]
    log.refresh_from_db()
    assert log.status == EmailLog.Status.SENT
    assert not Store.objects.filter(application=application).exists()


@pytest.mark.parametrize(
    "body", [{}, {"reason": ""}, {"reason": "   "}, {"reason": "x" * 501}]
)
def test_reject_requires_a_reason(
    admin_client: APIClient, body: dict[str, str]
) -> None:
    """Missing, blank or too long reasons answer 400 and change nothing."""
    application = _application()

    response = admin_client.post(reject_url(application.pk), body, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "reason" in response.json()["fields"]
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED


def test_rejecting_a_decided_application_answers_409(admin_client: APIClient) -> None:
    """A rejected application cannot be rejected again."""
    application = _decided(ApplicationStatus.REJECTED, reason="Outside the area")

    response = admin_client.post(
        reject_url(application.pk), {"reason": "Again"}, format="json"
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "status", [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]
)
def test_decided_applications_expose_no_decision_actions(admin_client, status):
    """Availability comes from the same server rule as decision enforcement."""
    application = _decided(status, reason="reason")
    item = admin_client.get(LIST_URL).json()["results"][0]
    assert item["id"] == str(application.pk)
    assert item["can_decide"] is False


def test_decision_availability_denies_without_request_context():
    """Serializing without an authorized request never advertises actions."""
    from modules.stores.api.serializers import StaffPartnerApplicationSerializer

    assert StaffPartnerApplicationSerializer(_application()).data["can_decide"] is False
