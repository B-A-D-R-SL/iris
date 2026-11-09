# AI contribution: 50% or more AI-generated
from typing import Any
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from modules.notifications.services import queue_set_password_email

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("language", "subject"),
    [
        ("en", "Set your Iris password"),
        ("fr", "Créez votre mot de passe Iris"),
    ],
)
def test_email_language_and_post_commit_delivery(
    language: str,
    subject: str,
    django_capture_on_commit_callbacks: Any,
) -> None:
    mailer = Mock()
    mailer.send.return_value = 1
    with django_capture_on_commit_callbacks(execute=True):
        queue_set_password_email(
            email="holder@example.test",
            token="secret",
            language=language,
            mailer=mailer,
        )
        mailer.send.assert_not_called()
    assert mailer.send.call_args.args[1] == subject
    assert "/invitation/secret" in mailer.send.call_args.kwargs["text"]


@pytest.mark.parametrize("failure", [RuntimeError("private@example.test secret"), None])
def test_delivery_failure_is_private_and_does_not_escape(
    failure: Exception | None,
    caplog: Any,
    django_capture_on_commit_callbacks: Any,
) -> None:
    mailer = Mock()
    mailer.send.side_effect = failure
    mailer.send.return_value = 0
    with django_capture_on_commit_callbacks(execute=True):
        queue_set_password_email(
            email="private@example.test", token="secret", language="en", mailer=mailer
        )
    assert "set_password_email_failed" in caplog.text
    assert "private@example.test" not in caplog.text
    assert "secret" not in caplog.text


@pytest.mark.parametrize(
    "url",
    [
        "",
        "javascript:alert(1)",
        "https://iris.test/?token=secret",
        "http://iris.test",
        "https://user:secret@iris.test",
    ],
)
def test_invalid_frontend_url_is_refused(url: str, settings: Any) -> None:
    settings.FRONTEND_URL = url
    with pytest.raises(ValidationError):
        queue_set_password_email(
            email="holder@example.test", token="secret", language="en"
        )


@pytest.mark.parametrize("backend", ["console", "filebased"])
def test_secret_links_cannot_be_sent_to_logging_backends(
    backend: str, settings: Any, capsys: Any
) -> None:
    settings.MAILERS = {
        "default": {"BACKEND": f"django.core.mail.backends.{backend}.EmailBackend"}
    }
    with pytest.raises(ValidationError):
        queue_set_password_email(
            email="holder@example.test", token="secret", language="en"
        )
    assert "secret" not in capsys.readouterr().out
