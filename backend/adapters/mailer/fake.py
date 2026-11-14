# AI contribution: 50% or more AI-generated
"""Reusable in-memory mailer; no message data leaves the test process."""

from collections.abc import Sequence
from typing import Any

from adapters.mailer.base import MailerError


class FakeMailer:
    def __init__(
        self, *, result: int | None = None, error: MailerError | None = None
    ) -> None:
        self.sent: list[dict[str, Any]] = []
        self.result = result
        self.error = error

    def send(
        self,
        to: Sequence[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
    ) -> int:
        if not to:
            raise ValueError("At least one recipient is required")
        if html is None and text is None:
            raise ValueError("At least one email body (text or html) is required")
        if self.error is not None:
            raise self.error from None
        if self.result == 0:
            return 0
        self.sent.append(
            {"to": list(to), "subject": subject, "html": html, "text": text}
        )
        return 1 if self.result is None else self.result


_fake_mailer = FakeMailer()


def get_fake_mailer() -> FakeMailer:
    """Return the fake shared by service and worker calls in one test process."""
    return _fake_mailer


def reset_fake_mailer() -> None:
    """Restore an empty successful fake between tests."""
    _fake_mailer.sent.clear()
    _fake_mailer.result = None
    _fake_mailer.error = None
