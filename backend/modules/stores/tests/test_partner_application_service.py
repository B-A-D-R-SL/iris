# AI contribution: 50% or more AI-generated
"""US-12 submit_application(): saving, duplicates and the confirmation email."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.utils import translation

from adapters.mailer.base import MailerError
from adapters.mailer.fake import get_fake_mailer
from modules.categories.tests.factories import CategoryFactory
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email
from modules.stores import services
from modules.stores.models import ApplicationStatus, PartnerApplication
from modules.stores.tests.factories import PartnerApplicationFactory

# Direct tests intentionally run without a worker-injected JobContext.
DIRECT_CONTEXT: Any = None


pytestmark = pytest.mark.usefixtures("notification_rules")


def values(**overrides: Any) -> dict[str, Any]:
    """Validated, normalized values, as the API serializer hands them over."""
    data: dict[str, Any] = {
        "business_name": "Boulangerie Exemple",
        "business_type": "bakery",
        "neq": None,
        "website": None,
        "street_number": "1234",
        "street_name": "rue Exemple",
        "unit": None,
        "city": "Montréal",
        "postal_code": "H2X 1Y4",
        "contact_first_name": "Alex",
        "contact_last_name": "Exemple",
        "contact_role": None,
        "contact_email": "owner@example.test",
        "contact_phone": "+15145550123",
        "goods_categories": ["bakery"],
        "expected_frequency": "weekly",
        "opening_hours": "lun-ven 9 h-18 h",
        "message": None,
        "consent_contact": True,
    }
    return {**data, **overrides}


@pytest.fixture
def categories(db: Any) -> None:
    CategoryFactory(code="bakery")
    CategoryFactory(code="dairy_eggs")
    CategoryFactory(code="retired", is_active=False)


@pytest.fixture
def queued_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Record background work without running a worker in the request."""
    queued: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: queued.append(kwargs))
    return queued


@pytest.mark.usefixtures("categories")
def test_submission_is_saved_as_submitted_without_an_account(
    django_capture_on_commit_callbacks: Any,
) -> None:
    users_before = get_user_model()._default_manager.count()
    with django_capture_on_commit_callbacks(execute=True):
        application = services.submit_application(values(), language="en")
    application.refresh_from_db()
    assert application.status == ApplicationStatus.SUBMITTED
    assert application.language == "en"
    assert application.consent_contact is True
    assert (
        get_user_model()._default_manager.count() == users_before
    )  # no account at this step


@pytest.mark.usefixtures("categories")
@pytest.mark.parametrize(
    ("language", "subject", "greeting"),
    [
        ("fr", "Nous avons reçu votre demande de partenariat", "Bonjour,"),
        ("en", "We received your partner application", "Hello,"),
    ],
)
def test_confirmation_email_is_sent_after_commit_in_the_contact_language(
    django_capture_on_commit_callbacks: Any,
    queued_emails: list[dict[str, Any]],
    language: str,
    subject: str,
    greeting: str,
) -> None:
    # rule: AC2, the applicant gets a confirmation email
    mailer = get_fake_mailer()
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        services.submit_application(values(), language=language)
        assert queued_emails == []
        assert mailer.sent == []  # nothing is sent before the commit
    assert len(callbacks) == 1
    callbacks[0]()
    assert mailer.sent == []  # enqueueing never performs transport
    [job] = queued_emails
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.language == language
    assert log.template_key == "partner_application_received"
    send_email(DIRECT_CONTEXT, **job)
    [email] = mailer.sent
    assert email["to"] == ["owner@example.test"]
    assert email["subject"] == subject
    assert email["text"].startswith(greeting)
    assert "Boulangerie Exemple" in email["text"]


@pytest.mark.usefixtures("categories")
def test_submission_queues_the_shared_delivery_job(
    django_capture_on_commit_callbacks: Any,
    queued_emails: list[dict[str, Any]],
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        services.submit_application(values(), language="fr")
    [job] = queued_emails
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.to_email == "owner@example.test"
    assert log.user_id is None
    assert log.attempts == 0
    assert job["context"] == {"business_name": "Boulangerie Exemple"}
    assert get_fake_mailer().sent == []


@pytest.mark.usefixtures("categories")
def test_rolled_back_submission_sends_no_email(
    django_capture_on_commit_callbacks: Any,
    queued_emails: list[dict[str, Any]],
) -> None:
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.submit_application(values(), language="fr")
        raise RuntimeError("caller failed after saving")
    assert callbacks == []
    assert queued_emails == []
    assert get_fake_mailer().sent == []
    assert not EmailLog.objects.exists()
    assert not PartnerApplication.objects.exists()


@pytest.mark.usefixtures("categories")
def test_email_failure_keeps_the_application(
    django_capture_on_commit_callbacks: Any,
    queued_emails: list[dict[str, Any]],
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        application = services.submit_application(values(), language="fr")
    get_fake_mailer().error = MailerError("transport_unavailable", retryable=True)
    [job] = queued_emails
    with pytest.raises(MailerError):
        send_email(DIRECT_CONTEXT, **job)
    assert PartnerApplication.objects.filter(pk=application.pk).exists()


@pytest.mark.usefixtures("categories")
@pytest.mark.parametrize("email", ["owner@example.test", "Owner@Example.TEST"])
def test_second_open_application_with_same_email_is_refused(email: str) -> None:
    # rule: BR-PARTNER-01 (AC3), refuse a duplicate open application
    PartnerApplicationFactory(contact_email="owner@example.test")
    with pytest.raises(services.ApplicationAlreadyOpen) as refused:
        services.submit_application(values(contact_email=email), language="fr")
    assert refused.value.email == email
    assert PartnerApplication.objects.count() == 1


@pytest.mark.usefixtures("categories")
def test_rejected_applicant_may_apply_again(
    django_capture_on_commit_callbacks: Any,
) -> None:
    # rule: BR-PARTNER-01, a rejected application does not block another submission
    PartnerApplicationFactory(
        contact_email="owner@example.test",
        status=ApplicationStatus.REJECTED,
        decision_reason="Generated reason",
    )
    with django_capture_on_commit_callbacks(execute=True):
        services.submit_application(values(), language="fr")
    assert PartnerApplication.objects.count() == 2


@pytest.mark.usefixtures("categories")
@pytest.mark.parametrize(
    "codes", [["retired"], ["unknown_code"], ["bakery", "unknown_code"], []]
)
def test_goods_categories_must_be_active_codes(codes: list[str]) -> None:
    with pytest.raises(ValidationError) as refused:
        services.submit_application(values(goods_categories=codes), language="en")
    with translation.override("en"):
        assert refused.value.message_dict == {
            "goods_categories": ["Choose types of goods from the list."]
        }
    assert not PartnerApplication.objects.exists()


@pytest.mark.usefixtures("categories")
def test_unsupported_language_falls_back_to_french(
    django_capture_on_commit_callbacks: Any,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        application = services.submit_application(values(), language="de")
    assert application.language == "fr"


@pytest.mark.django_db(transaction=True)
def test_simultaneous_submissions_with_one_email_save_exactly_one() -> None:
    # rule: BR-PARTNER-01 (AC3), the partial unique index settles concurrent requests
    CategoryFactory(code="bakery")

    def submit(_: int) -> str:
        close_old_connections()
        try:
            services.submit_application(values(), language="fr")
            return "saved"
        except services.ApplicationAlreadyOpen:
            return "refused"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=6) as workers:
        results = list(workers.map(submit, range(6)))
    assert results.count("saved") == 1
    assert results.count("refused") == 5
    assert PartnerApplication.objects.count() == 1
