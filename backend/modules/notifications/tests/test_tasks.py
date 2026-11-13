# AI contribution: 50% or more AI-generated
"""Household status email task adapter tests."""

from collections.abc import Sequence
from typing import Any

import pytest

from modules.notifications.tasks import deliver_household_status_email


class RecordingMailer:
    """Record calls and return a configured adapter result."""

    def __init__(self, result: int = 1) -> None:
        self.result = result
        self.sent: list[dict[str, Any]] = []

    def send(
        self,
        to: Sequence[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
    ) -> int:
        self.sent.append({"to": list(to), "subject": subject, "text": text})
        return self.result


class FailingMailer:
    """Raise the same kind of failure as an unavailable SMTP service."""

    def send(self, *args: Any, **kwargs: Any) -> int:
        raise ConnectionError("mail unavailable")


def test_delivery_uses_the_mail_adapter() -> None:
    """The worker passes the queued content to its adapter."""
    mailer = RecordingMailer()
    deliver_household_status_email(
        mailer, "holder@example.test", "Status changed", "Status changed"
    )
    assert mailer.sent == [
        {
            "to": ["holder@example.test"],
            "subject": "Status changed",
            "text": "Status changed",
        }
    ]


@pytest.mark.parametrize("mailer", [FailingMailer(), RecordingMailer(result=0)])
def test_delivery_failure_is_contained_and_logged(
    mailer: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """An adapter exception or refusal stays inside the background job."""
    deliver_household_status_email(
        mailer, "holder@example.test", "Status changed", "Status changed"
    )
    record = next(
        item
        for item in caplog.records
        if item.message == "household_status_email_failed"
    )
    assert getattr(record, "event", None) == "household_status_email_failed"
