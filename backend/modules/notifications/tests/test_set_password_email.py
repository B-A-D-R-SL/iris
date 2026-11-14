# AI contribution: 50% or more AI-generated
"""US-18 walk-in set-password email on US-57's shared queued delivery."""

from typing import Any

import pytest
from django.db import transaction

from modules.notifications.models import EmailLog
from modules.notifications.services import queue_set_password_email
from modules.notifications.tasks import send_email

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("notification_rules")]
ORIGIN = "https://iris.example.test"
TOKEN = "A" * 43


@pytest.fixture
def queued(monkeypatch: pytest.MonkeyPatch, settings: Any) -> list[dict[str, Any]]:
    """Capture post-commit task arguments without running a worker."""
    settings.PUBLIC_APP_ORIGIN = ORIGIN
    jobs: list[dict[str, Any]] = []
    monkeypatch.setattr(send_email, "configure", lambda **kwargs: send_email)
    monkeypatch.setattr(send_email, "defer", lambda **kwargs: jobs.append(kwargs))
    return jobs


@pytest.mark.parametrize(
    ("language", "saved"), [("en", "en"), ("fr", "fr"), ("", "fr")]
)
def test_link_is_queued_after_commit_in_the_holder_language(
    language: str,
    saved: str,
    queued: list[dict[str, Any]],
    django_capture_on_commit_callbacks: Any,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        log = queue_set_password_email(
            email="holder@example.test", token=TOKEN, language=language
        )
        assert queued == []
    [job] = queued
    assert job["email_log_id"] == str(log.pk)
    assert job["context"] == {"invitation_url": f"{ORIGIN}/invitation/{TOKEN}"}
    log.refresh_from_db()
    assert log.template_key == "walk_in_set_password"
    assert log.language == saved
    assert log.to_email == "holder@example.test"
    assert TOKEN not in repr(EmailLog.objects.values().get(pk=log.pk))


@pytest.mark.parametrize("origin", [None, "", "https://iris.example.test/path"])
def test_bad_origin_is_a_failed_log_not_an_error(
    origin: str | None, settings: Any, queued: list[dict[str, Any]]
) -> None:
    settings.PUBLIC_APP_ORIGIN = origin
    log = queue_set_password_email(
        email="holder@example.test", token=TOKEN, language="en"
    )
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "email_configuration_invalid"
    assert queued == []


def test_rollback_queues_nothing(
    queued: list[dict[str, Any]], django_capture_on_commit_callbacks: Any
) -> None:
    with (
        django_capture_on_commit_callbacks(execute=True) as callbacks,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        queue_set_password_email(
            email="holder@example.test", token=TOKEN, language="en"
        )
        raise RuntimeError("Cancel")
    assert callbacks == []
    assert queued == []
    assert not EmailLog.objects.exists()
