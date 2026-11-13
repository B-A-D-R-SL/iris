# AI contribution: 50% or more AI-generated
"""Provider contracts: payloads, acceptance and safe delivery errors."""

# Adapter contract tests simulate SMTP failures without network delivery.
from smtplib import SMTPDataError  # noqa: TID251
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError
from azure.core.polling import LROPoller
from django.test import override_settings

from adapters.mailer.azure import AzureMailer, _DeadlinePolling
from adapters.mailer.base import MailerError
from adapters.mailer.factory import get_mailer
from adapters.mailer.fake import FakeMailer, get_fake_mailer, reset_fake_mailer
from adapters.mailer.smtp import SmtpMailer


@pytest.fixture
def azure_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock()
    client.__enter__.return_value = client
    client.begin_send.return_value.done.return_value = True
    client.begin_send.return_value.result.return_value = {"status": "Succeeded"}
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(
        "adapters.mailer.azure.EmailClient.from_connection_string", constructor
    )
    client.constructor = constructor
    return client


@override_settings(
    DEFAULT_FROM_EMAIL="DoNotReply@verified.azurecomm.net",
    AZURE_COMMUNICATION_CONNECTION_STRING="synthetic-credential",
    AZURE_EMAIL_SEND_TIMEOUT_SECONDS=3,
)
def test_azure_maps_multipart_and_waits_for_acceptance(azure_client: MagicMock) -> None:
    assert (
        AzureMailer().send(["recipient@example.test"], "Subject", "<p>Body</p>", "Body")
        == 1
    )
    payload = azure_client.begin_send.call_args.args[0]
    assert payload == {
        "senderAddress": "DoNotReply@verified.azurecomm.net",
        "recipients": {"to": [{"address": "recipient@example.test"}]},
        "content": {"subject": "Subject", "plainText": "Body", "html": "<p>Body</p>"},
    }
    assert azure_client.constructor.call_args.kwargs == {
        "connection_timeout": 3,
        "read_timeout": 3,
        "retry_total": 0,
        "logging_enable": False,
    }
    assert (
        0 < azure_client.begin_send.return_value.wait.call_args.kwargs["timeout"] <= 3
    )
    azure_client.begin_send.return_value.result.assert_called_once_with(timeout=0)


def test_azure_does_not_count_an_unfinished_operation(azure_client: MagicMock) -> None:
    poller = azure_client.begin_send.return_value
    poller.done.return_value = False
    with pytest.raises(MailerError, match="provider_timeout") as failure:
        AzureMailer().send(["recipient@example.test"], "Subject", text="Body")
    assert failure.value.retryable
    poller.result.assert_not_called()


@pytest.mark.parametrize("status", ["Failed", "Canceled", "Running", None])
def test_azure_requires_final_succeeded_status(
    azure_client: MagicMock, status: str | None
) -> None:
    azure_client.begin_send.return_value.result.return_value = {"status": status}
    with pytest.raises(MailerError, match="provider_rejected") as failure:
        AzureMailer().send(["recipient@example.test"], "Subject", text="Body")
    assert not failure.value.retryable


@pytest.mark.parametrize(
    ("status", "retryable"), [(400, False), (401, False), (429, True), (503, True)]
)
def test_azure_maps_http_errors_without_retaining_provider_text(
    azure_client: MagicMock, status: int, retryable: bool
) -> None:
    error = HttpResponseError("secret-token recipient@example.test body text")
    error.status_code = status
    azure_client.begin_send.side_effect = error
    with pytest.raises(MailerError) as failure:
        AzureMailer().send(["recipient@example.test"], "Subject", text="Body")
    assert str(failure.value) == "provider_rejected"
    assert failure.value.retryable is retryable
    assert failure.value.__suppress_context__


def test_azure_network_errors_are_sanitized(azure_client: MagicMock) -> None:
    azure_client.begin_send.side_effect = ConnectionError("secret provider response")
    with pytest.raises(MailerError, match="^transport_unavailable$"):
        AzureMailer().send(["recipient@example.test"], "Subject", text="Body")


def test_background_polling_stops_when_retry_after_exceeds_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"now": 0.0}
    monkeypatch.setattr("adapters.mailer.azure.monotonic", lambda: clock["now"])
    wake = MagicMock()
    wake.wait.side_effect = lambda delay: clock.update(now=clock["now"] + delay)
    monkeypatch.setattr("adapters.mailer.azure.Event", lambda: wake)
    polling = _DeadlinePolling(deadline=3, request_timeout=3)
    polling.polling = MagicMock()
    polling.polling.finished.return_value = False
    response = MagicMock()
    response.http_response.headers = {"retry-after": "999"}
    polling.initialize(MagicMock(), response, MagicMock())
    with pytest.raises(MailerError, match="^provider_timeout$"):
        polling.run()
    wake.wait.assert_called_once_with(3)
    polling.polling.update_status.assert_not_called()


def test_sdk_poller_completes_using_the_bounded_polling_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"now": 0.0}
    monkeypatch.setattr("adapters.mailer.azure.monotonic", lambda: clock["now"])
    wake = MagicMock()
    wake.wait.side_effect = lambda delay: clock.update(now=clock["now"] + delay)
    monkeypatch.setattr("adapters.mailer.azure.Event", lambda: wake)
    polling = _DeadlinePolling(deadline=3, request_timeout=3)
    delegate = MagicMock()
    polling.polling = delegate
    delegate.finished.side_effect = lambda: clock["now"] == 2
    delegate.status.return_value = "Succeeded"
    delegate.resource.return_value = {"status": "Succeeded"}
    delegate.get_continuation_token.return_value = "opaque-sdk-token"
    response = MagicMock()
    response.http_response.headers = {"retry-after": "invalid"}
    poller = LROPoller(MagicMock(), response, MagicMock(), polling)
    assert poller.result(timeout=1) == {"status": "Succeeded"}
    assert poller.done() and poller.status() == "Succeeded"
    assert poller.continuation_token() == "opaque-sdk-token"
    assert delegate.update_status.call_count == 2


def test_mailer_error_normalizes_unrecognized_provider_text() -> None:
    error = MailerError("recipient@example.test token=secret message body")
    assert error.code == "delivery_failed"
    assert str(error) == "delivery_failed"


@pytest.mark.parametrize(("status", "retryable"), [(450, True), (550, False)])
def test_smtp_maps_provider_status_without_response_text(
    monkeypatch: pytest.MonkeyPatch, status: int, retryable: bool
) -> None:
    monkeypatch.setattr(
        "adapters.mailer.smtp.EmailMultiAlternatives.send",
        MagicMock(side_effect=SMTPDataError(status, b"secret recipient/body")),
    )
    with pytest.raises(MailerError, match="^provider_rejected$") as failure:
        SmtpMailer().send(["recipient@example.test"], "Subject", text="Body")
    assert failure.value.retryable is retryable
    assert failure.value.__suppress_context__


def test_smtp_network_errors_are_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "adapters.mailer.smtp.EmailMultiAlternatives.send",
        MagicMock(side_effect=ConnectionError("private details")),
    )
    with pytest.raises(MailerError, match="^transport_unavailable$"):
        SmtpMailer().send(["recipient@example.test"], "Subject", text="Body")


def test_fake_records_success_and_can_refuse_or_fail() -> None:
    mailer = FakeMailer()
    assert mailer.send(["one@example.test"], "Subject", "<p>Body</p>", "Body") == 1
    assert mailer.sent == [
        {
            "to": ["one@example.test"],
            "subject": "Subject",
            "html": "<p>Body</p>",
            "text": "Body",
        }
    ]
    mailer.result = 0
    assert mailer.send(["one@example.test"], "Subject", text="Body") == 0
    mailer.error = MailerError("transport_unavailable")
    with pytest.raises(MailerError):
        mailer.send(["one@example.test"], "Subject", text="Body")
    assert len(mailer.sent) == 1


def test_factory_selects_each_adapter_and_rejects_unknown_settings() -> None:
    for name, cls in [
        ("smtp", SmtpMailer),
        ("azure", AzureMailer),
        ("fake", FakeMailer),
    ]:
        with override_settings(MAILER_ADAPTER=name):
            assert isinstance(get_mailer(), cls)
    with override_settings(MAILER_ADAPTER="unknown"), pytest.raises(MailerError):
        get_mailer()


def test_shared_fake_can_be_reset() -> None:
    mailer = get_fake_mailer()
    mailer.send(["recipient@example.test"], "Subject", text="Body")
    mailer.result = 0
    mailer.error = MailerError("provider_rejected", retryable=False)
    reset_fake_mailer()
    assert mailer is get_fake_mailer()
    assert mailer.sent == []
    assert mailer.result is None and mailer.error is None
