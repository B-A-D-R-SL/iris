# AI contribution: 50% or more AI-generated
"""Contract for email delivery adapters, separate from business modules."""

from collections.abc import Sequence
from typing import Protocol


class MailerError(Exception):
    """A fixed internal error code safe to persist or pass to a job runner."""

    _CODES = frozenset(
        {
            "delivery_failed",
            "provider_rejected",
            "transport_unavailable",
            "provider_timeout",
            "mailer_not_configured",
            "email_configuration_invalid",
            "delivery_unavailable",
            "email_cleanup_failed",
        }
    )

    def __init__(self, code: str, *, retryable: bool = True) -> None:
        self.code = code if code in self._CODES else "delivery_failed"
        self.retryable = retryable
        super().__init__(self.code)


class Mailer(Protocol):
    def send(
        self,
        to: Sequence[str],
        subject: str,
        html: str | None = None,
        text: str | None = None,
    ) -> int: ...
