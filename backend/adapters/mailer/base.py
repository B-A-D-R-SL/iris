# AI contribution: 50% or more AI-generated
"""Contract for email delivery adapters, separate from business modules."""

from collections.abc import Sequence
from typing import Protocol


class MailerError(RuntimeError):
    """An email transport failed to deliver a message."""


class Mailer(Protocol):
    def send(
        self,
        to: Sequence[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
    ) -> int: ...
