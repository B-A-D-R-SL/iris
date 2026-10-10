# AI contribution: 50% or more AI-generated
"""Meaningful tests for developer bootstrap and the mail adapter."""

from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from adapters.mailer.smtp import SmtpMailer


@pytest.mark.django_db
def test_dev_admin_is_created_and_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_DEV_ADMIN_EMAIL", "admin@iris.local")
    monkeypatch.setenv("DJANGO_DEV_ADMIN_PASSWORD", "local-test-password")

    with override_settings(DEBUG=True):
        call_command("create_dev_admin", stdout=StringIO())
        call_command("create_dev_admin", stdout=StringIO())

    assert User.objects.filter(username="admin@iris.local").count() == 1
    user = User.objects.get(username="admin@iris.local")
    assert user.email == "admin@iris.local"
    assert user.is_staff and user.is_superuser
    assert user.check_password("local-test-password")


def test_dev_admin_refuses_non_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_DEV_ADMIN_PASSWORD", "local-test-password")
    with override_settings(DEBUG=False), pytest.raises(CommandError, match="DEBUG=True"):
        call_command("create_dev_admin", stdout=StringIO())


@override_settings(
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}},
    DEFAULT_FROM_EMAIL="noreply@iris.local",
)
def test_smtp_adapter_sends_plain_email() -> None:
    sent = SmtpMailer().send(
        to=["recipient@iris.local"], subject="Test notification", text="Hello Iris"
    )

    assert sent == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].body == "Hello Iris"
    assert mail.outbox[0].to == ["recipient@iris.local"]


def test_smtp_adapter_requires_message_content() -> None:
    with pytest.raises(ValueError, match="email body"):
        SmtpMailer().send(["recipient@iris.local"], "Invalid")
