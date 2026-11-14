# AI contribution: 50% or more AI-generated
"""Azure Communication Services delivery with bounded waits and safe failures."""

import logging
from collections.abc import Mapping, Sequence
from math import isfinite
from threading import Event
from time import monotonic
from typing import Any

from azure.communication.email import EmailClient
from azure.core.exceptions import HttpResponseError
from azure.core.polling import PollingMethod
from azure.core.polling.base_polling import LROBasePolling
from django.conf import settings

from adapters.mailer.base import MailerError

logger = logging.getLogger("iris.notifications")


class _DeadlinePolling(PollingMethod[dict[str, Any]]):
    """Stop the SDK's polling thread at the same deadline as the caller's wait."""

    def __init__(self, deadline: float, request_timeout: float) -> None:
        self.deadline = deadline
        self.delay = 1.0
        self.polling: LROBasePolling[Any, Any, Any] = LROBasePolling(
            timeout=1,
            lro_options={"final-state-via": "azure-async-operation"},
            connection_timeout=request_timeout,
            read_timeout=request_timeout,
            retry_total=0,
            logging_enable=False,
            raw_response_hook=self._read_delay,
        )

    def _read_delay(self, response: Any) -> None:
        try:
            delay = float(response.http_response.headers.get("retry-after", "1"))
            if not isfinite(delay):
                raise ValueError
        except (TypeError, ValueError):
            self.delay = 1.0
            logger.warning(
                "azure_retry_after_invalid",
                extra={"event": "azure_retry_after_invalid"},
            )
        else:
            self.delay = max(1.0, delay)

    def initialize(self, client: Any, initial_response: Any, callback: Any) -> None:
        self._read_delay(initial_response)
        self.polling.initialize(client, initial_response, callback)

    def run(self) -> None:
        while not self.finished():
            remaining = self.deadline - monotonic()
            if remaining <= 0:
                raise MailerError("provider_timeout")
            Event().wait(min(self.delay, remaining))
            if monotonic() >= self.deadline:
                raise MailerError("provider_timeout")
            self.polling.update_status()

    def status(self) -> str:
        return self.polling.status()

    def finished(self) -> bool:
        return self.polling.finished()

    def resource(self) -> dict[str, Any]:
        return self.polling.resource()

    def get_continuation_token(self) -> str:
        return self.polling.get_continuation_token()


class AzureMailer:
    # Size/complexity exception: one client lifetime and try boundary apply the
    # same absolute deadline and sanitized error mapping to client creation,
    # submission and completion checks; acceptance is counted at one return point.
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

        content = {"subject": subject}
        if text is not None:
            content["plainText"] = text
        if html is not None:
            content["html"] = html
        message = {
            "senderAddress": settings.DEFAULT_FROM_EMAIL,
            "recipients": {"to": [{"address": address} for address in to]},
            "content": content,
        }
        timeout = settings.AZURE_EMAIL_SEND_TIMEOUT_SECONDS
        deadline = monotonic() + timeout
        try:
            with EmailClient.from_connection_string(
                settings.AZURE_COMMUNICATION_CONNECTION_STRING,
                connection_timeout=timeout,
                read_timeout=timeout,
                retry_total=0,
                logging_enable=False,
            ) as client:
                poller = client.begin_send(
                    message,
                    polling=_DeadlinePolling(deadline, timeout),
                    logging_enable=False,
                )
                poller.wait(timeout=max(0, deadline - monotonic()))
                # Azure's result(timeout) can return before completion; verify both.
                if not poller.done():
                    raise MailerError("provider_timeout")
                result = poller.result(timeout=0)
                if (
                    not isinstance(result, Mapping)
                    or result.get("status") != "Succeeded"
                ):
                    raise MailerError("provider_rejected", retryable=False)
        except MailerError:
            raise
        except HttpResponseError as exc:
            status = exc.status_code
            retryable = status is None or status in {408, 429} or status >= 500
            raise MailerError("provider_rejected", retryable=retryable) from None
        except ValueError:
            raise MailerError("mailer_not_configured", retryable=False) from None
        except Exception:  # noqa: BLE001 - SDK errors may contain content or credentials.
            raise MailerError("transport_unavailable") from None
        return 1
