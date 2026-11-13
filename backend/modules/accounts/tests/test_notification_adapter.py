# AI contribution: 50% or more AI-generated
"""Authentication emails enter the shared queue with reviewed scalar context."""

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


def test_unknown_authentication_mail_fails_without_inline_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adding an allauth mail type requires an explicit reviewed mapping."""
    queued: list[Any] = []
    monkeypatch.setattr(
        "modules.accounts.adapter.notification_services.send",
        lambda *args: queued.append(args),
    )
    with pytest.raises(
        ValueError, match="^Unsupported authentication email template\\.$"
    ):
        AccountAdapter().send_mail("unreviewed-secret", "recipient@example.test", {})
    assert queued == []
    assert get_fake_mailer().sent == []


def test_missing_action_url_is_rejected_before_queueing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queued: list[Any] = []
    monkeypatch.setattr(
        "modules.accounts.adapter.notification_services.send",
        lambda *args: queued.append(args),
    )
    with pytest.raises(
        TypeError, match="^Authentication email requires an action URL\\.$"
    ):
        AccountAdapter().send_mail(
            "account/email/password_reset_key", "a@example.test", {}
        )
    assert queued == []


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
