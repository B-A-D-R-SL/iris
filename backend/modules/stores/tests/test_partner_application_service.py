# AI contribution: 50% or more AI-generated
"""US-12 submit_application(): saving, duplicates and the confirmation email."""

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.utils import translation

from modules.categories.tests.factories import CategoryFactory
from modules.stores import services
from modules.stores.models import ApplicationStatus, PartnerApplication
from modules.stores.tests.factories import PartnerApplicationFactory


class RecordingMailer:
    """Test double for the mailer adapter."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    def send(
        self,
        to: Sequence[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
    ) -> int:
        self.sent.append({"to": list(to), "subject": subject, "text": text})
        return 1


class FailingMailer:
    def send(self, *args: Any, **kwargs: Any) -> int:
        raise ConnectionError("smtp down for owner@example.test")


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


@pytest.mark.usefixtures("categories")
def test_submission_is_saved_as_submitted_without_an_account(
    django_capture_on_commit_callbacks: Any,
) -> None:
    users_before = get_user_model()._default_manager.count()
    with django_capture_on_commit_callbacks(execute=True):
        application = services.submit_application(
            values(), language="en", mailer=RecordingMailer()
        )
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
    django_capture_on_commit_callbacks: Any, language: str, subject: str, greeting: str
) -> None:
    # rule: AC2, the applicant gets a confirmation email
    mailer = RecordingMailer()
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        services.submit_application(values(), language=language, mailer=mailer)
        assert mailer.sent == []  # nothing is sent before the commit
    assert len(callbacks) == 1
    callbacks[0]()
    [email] = mailer.sent
    assert email["to"] == ["owner@example.test"]
    assert email["subject"] == subject
    assert email["text"].startswith(greeting)
    assert "Boulangerie Exemple" in email["text"]


@pytest.mark.usefixtures("categories")
def test_default_mailer_delivers_through_django_mail(
    django_capture_on_commit_callbacks: Any,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        services.submit_application(values(), language="fr")
    assert [message.to for message in mail.outbox] == [["owner@example.test"]]


@pytest.mark.usefixtures("categories")
def test_rolled_back_submission_sends_no_email(
    django_capture_on_commit_callbacks: Any,
) -> None:
    mailer = RecordingMailer()
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.submit_application(values(), language="fr", mailer=mailer)
        raise RuntimeError("caller failed after saving")
    assert callbacks == []
    assert mailer.sent == []
    assert not PartnerApplication.objects.exists()


@pytest.mark.usefixtures("categories")
def test_email_failure_keeps_the_application_and_logs_no_personal_data(
    django_capture_on_commit_callbacks: Any, caplog: pytest.LogCaptureFixture
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        application = services.submit_application(
            values(), language="fr", mailer=FailingMailer()
        )
    assert PartnerApplication.objects.filter(pk=application.pk).exists()
    assert "partner_application_email_failed" in caplog.text
    assert "owner@example.test" not in caplog.text
    assert "smtp down" not in caplog.text


@pytest.mark.usefixtures("categories")
@pytest.mark.parametrize("email", ["owner@example.test", "Owner@Example.TEST"])
def test_second_open_application_with_same_email_is_refused(email: str) -> None:
    # rule: AC3, an open application with the same contact email
    PartnerApplicationFactory(contact_email="owner@example.test")
    with pytest.raises(services.ApplicationAlreadyOpen) as refused:
        services.submit_application(
            values(contact_email=email), language="fr", mailer=RecordingMailer()
        )
    assert refused.value.email == email
    assert PartnerApplication.objects.count() == 1


@pytest.mark.usefixtures("categories")
def test_rejected_applicant_may_apply_again(
    django_capture_on_commit_callbacks: Any,
) -> None:
    PartnerApplicationFactory(
        contact_email="owner@example.test",
        status=ApplicationStatus.REJECTED,
        decision_reason="Generated reason",
    )
    with django_capture_on_commit_callbacks(execute=True):
        services.submit_application(values(), language="fr", mailer=RecordingMailer())
    assert PartnerApplication.objects.count() == 2


@pytest.mark.usefixtures("categories")
@pytest.mark.parametrize(
    "codes", [["retired"], ["unknown_code"], ["bakery", "unknown_code"], []]
)
def test_goods_categories_must_be_active_codes(codes: list[str]) -> None:
    with pytest.raises(ValidationError) as refused:
        services.submit_application(
            values(goods_categories=codes), language="en", mailer=RecordingMailer()
        )
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
        application = services.submit_application(
            values(), language="de", mailer=RecordingMailer()
        )
    assert application.language == "fr"


@pytest.mark.django_db(transaction=True)
def test_simultaneous_submissions_with_one_email_save_exactly_one() -> None:
    # rule: AC3 under concurrency; the partial unique index settles the race
    CategoryFactory(code="bakery")

    def submit(_: int) -> str:
        close_old_connections()
        try:
            services.submit_application(
                values(), language="fr", mailer=RecordingMailer()
            )
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
