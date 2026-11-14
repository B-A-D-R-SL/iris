# AI contribution: 50% or more AI-generated
"""Authentication emails enter the shared queue with reviewed scalar context."""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from django.test import RequestFactory
from django.utils import translation

from adapters.mailer.fake import get_fake_mailer
from modules.accounts.adapter import AccountAdapter
from modules.accounts.tests.factories import UserFactory
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email

# Direct tests intentionally run without a worker-injected JobContext.
DIRECT_CONTEXT: Any = None


pytestmark = pytest.mark.django_db
APP_ORIGIN = "https://iris.example.test"


@pytest.fixture
def authentication_mail_events(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> Iterator[pytest.LogCaptureFixture]:
    """Capture raw account-mail events before formatter filtering could hide data."""
    logger = logging.getLogger("iris.auth")
    monkeypatch.setattr(logger, "propagate", False)
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger=logger.name):
            yield caplog
    finally:
        logger.removeHandler(caplog.handler)


def _assert_private_skip_event(
    record: logging.LogRecord, sensitive_values: tuple[str, ...]
) -> None:
    assert record.name == "iris.auth"
    assert record.levelno == logging.INFO
    assert record.getMessage() == "authentication_email_skipped"
    assert vars(record)["event"] == "authentication_email_skipped"
    assert record.args == ()
    assert record.exc_info is None
    assert record.stack_info is None
    standard = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
    assert set(vars(record)) - standard == {"event"}
    for value in sensitive_values:
        assert value not in str(vars(record))


@pytest.mark.parametrize(
    ("prefix", "source", "key", "destination"),
    [
        (
            "account/email/email_confirmation",
            "activate_url",
            "account_confirmation",
            "confirmation_url",
        ),
        (
            "account/email/email_confirmation_signup",
            "activate_url",
            "account_confirmation",
            "confirmation_url",
        ),
        (
            "account/email/password_reset_key",
            "password_reset_url",
            "password_reset",
            "reset_url",
        ),
    ],
)
def test_supported_mail_preserves_user_locale_and_discards_allauth_context(
    monkeypatch: pytest.MonkeyPatch,
    prefix: str,
    source: str,
    key: str,
    destination: str,
) -> None:
    """Objects and raw allauth keys never become durable queue arguments."""
    user: Any = UserFactory(preferred_language="en")
    request = RequestFactory().get("/")
    request.LANGUAGE_CODE = "fr"
    queued: list[tuple[Any, str, dict[str, str]]] = []
    monkeypatch.setattr(
        "modules.accounts.adapter.notification_services.send",
        lambda recipient, template, context: queued.append(
            (recipient, template, context)
        ),
    )
    url = APP_ORIGIN + "/account-action/example-token"
    AccountAdapter().send_mail(
        prefix,
        user.email,
        {
            source: url,
            "user": user,
            "request": request,
            "current_site": object(),
            "key": "raw-secret",
            "password": "must-never-be-queued",
        },
    )
    assert queued == [(user, key, {destination: url, "language": "en"})]


@pytest.mark.parametrize(
    ("requested", "expected"), [("en-CA", "en"), ("fr-CA", "fr"), ("de", "fr")]
)
def test_email_only_recipient_uses_request_language(
    monkeypatch: pytest.MonkeyPatch, requested: str, expected: str
) -> None:
    """No recipient account still gives a deterministic supported language."""
    request = RequestFactory().get("/")
    request.LANGUAGE_CODE = requested
    adapter = AccountAdapter()
    adapter.request = request
    queued: list[dict[str, str]] = []
    monkeypatch.setattr(
        "modules.accounts.adapter.notification_services.send",
        lambda recipient, template, context: queued.append(context),
    )
    adapter.send_mail(
        "account/email/password_reset_key",
        "recipient@example.test",
        {"password_reset_url": APP_ORIGIN + "/reset/example-token"},
    )
    assert queued[0]["language"] == expected


def test_secondary_address_keeps_the_accounts_saved_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A confirmation may target an address different from the user's login email."""
    user: Any = UserFactory(preferred_language="en")
    queued: list[tuple[Any, dict[str, str]]] = []
    monkeypatch.setattr(
        "modules.accounts.adapter.notification_services.send",
        lambda recipient, template, context: queued.append((recipient, context)),
    )
    AccountAdapter().send_mail(
        "account/email/email_confirmation",
        "secondary@example.test",
        {"user": user, "activate_url": APP_ORIGIN + "/confirm/example-token"},
    )
    assert queued == [
        (
            "secondary@example.test",
            {
                "confirmation_url": APP_ORIGIN + "/confirm/example-token",
                "language": "en",
            },
        )
    ]


@pytest.mark.parametrize(
    "prefix",
    [
        "account/email/unknown_account",
        "account/email/account_already_exists",
        "unreviewed-secret-prefix",
    ],
)
def test_unsupported_authentication_mail_is_skipped_without_delivery(
    monkeypatch: pytest.MonkeyPatch,
    authentication_mail_events: pytest.LogCaptureFixture,
    prefix: str,
) -> None:
    """Unmapped allauth mail cannot fail its caller or fall back to inline SMTP."""
    queued: list[Any] = []
    inline: list[Any] = []
    monkeypatch.setattr(
        "modules.accounts.adapter.notification_services.send",
        lambda *args: queued.append(args),
    )
    monkeypatch.setattr(
        "allauth.account.adapter.DefaultAccountAdapter.send_mail",
        lambda *args: inline.append(args),
    )
    context = {
        "key": "reset-token-sentinel",
        "password": "credential-sentinel",
        "provider_diagnostic": "provider-detail-sentinel",
    }
    recipient = "private-recipient@example.test"
    AccountAdapter().send_mail(prefix, recipient, context)
    assert queued == []
    assert inline == []
    assert get_fake_mailer().sent == []
    assert not EmailLog.objects.exists()
    [record] = authentication_mail_events.records
    _assert_private_skip_event(record, (prefix, recipient, *context.values()))


@pytest.mark.parametrize(
    "context",
    [
        {},
        {"password_reset_url": None},
        {"password_reset_url": 42},
        {"password_reset_url": {"token": "private-action-sentinel"}},
    ],
    ids=["missing", "null", "integer", "object"],
)
def test_invalid_action_url_records_failure_without_queueing(
    settings: Any,
    django_capture_on_commit_callbacks: Any,
    monkeypatch: pytest.MonkeyPatch,
    context: dict[str, object],
) -> None:
    """The real notification service records malformed action data as failed mail."""
    settings.PUBLIC_APP_ORIGIN = APP_ORIGIN
    queued: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: queued.append(kwargs))
    with django_capture_on_commit_callbacks(execute=True):
        AccountAdapter().send_mail(
            "account/email/password_reset_key", "a@example.test", context
        )
    log = EmailLog.objects.get(template_key="password_reset")
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_configuration_invalid"
    assert log.attempts == 0 and log.sent_at is None
    assert not queued and not get_fake_mailer().sent


@pytest.mark.usefixtures("notification_rules")
def test_authentication_email_uses_committed_log_and_background_worker(
    settings: Any,
    django_capture_on_commit_callbacks: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bridge cannot bypass logging, locale capture or delayed transport."""
    settings.PUBLIC_APP_ORIGIN = APP_ORIGIN
    user: Any = UserFactory(preferred_language="en")
    queued: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: queued.append(kwargs))
    with django_capture_on_commit_callbacks(execute=True):
        AccountAdapter().send_mail(
            "account/email/password_reset_key",
            user.email,
            {"user": user, "password_reset_url": APP_ORIGIN + "/reset/example-token"},
        )
        assert queued == []
        assert get_fake_mailer().sent == []
    [job] = queued
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.user_id == user.pk
    assert log.language == "en"
    assert job["context"] == {"reset_url": APP_ORIGIN + "/reset/example-token"}
    with translation.override("fr"):
        send_email(DIRECT_CONTEXT, **job)
    [message] = get_fake_mailer().sent
    assert message["to"] == [user.email]
    assert "reset" in message["subject"].lower()
    log.refresh_from_db()
    assert log.status == "sent"


def test_email_delivery_bridge_does_not_open_public_signup() -> None:
    assert AccountAdapter().is_open_for_signup(RequestFactory().get("/")) is False
