# AI contribution: 50% or more AI-generated
"""AzureLayoutReader against a fake Document Intelligence client (no cloud calls)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from azure.core.exceptions import HttpResponseError

from azure_layout_reader import AzureLayoutReader
from reader import DocumentReadError

FIXTURE = Path(__file__).parent / "fixtures" / "layout-notice-003.json"
OPERATION_ID = "op-123"


class FakeResult:
    def __init__(self, raw: dict):
        self.raw = raw

    def as_dict(self) -> dict:
        return self.raw


class FakePoller:
    def __init__(self, outcome, done: bool = True):
        self.outcome = outcome
        self._done = done
        self.details = {"operation_id": OPERATION_ID}
        self.timeout: float | None = None

    def result(self, timeout: float | None = None):
        self.timeout = timeout
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome

    def done(self) -> bool:
        return self._done


class FakeClient:
    def __init__(self, poller: FakePoller | Exception, delete_error: Exception | None = None):
        self.poller = poller
        self.delete_error = delete_error
        self.analyzed: list[tuple] = []
        self.deleted: list[tuple[str, str]] = []

    def begin_analyze_document(self, model_id: str, body: bytes, **kwargs):
        self.analyzed.append((model_id, body, kwargs))
        if isinstance(self.poller, Exception):
            raise self.poller
        return self.poller

    def delete_analyze_result(self, model_id: str, result_id: str) -> None:
        self.deleted.append((model_id, result_id))
        if self.delete_error:
            raise self.delete_error


def fixture_result() -> FakeResult:
    return FakeResult(json.loads(FIXTURE.read_text("utf-8")))


def test_read_notice_returns_the_parsed_reading_and_sends_raw_bytes():
    client = FakeClient(FakePoller(fixture_result()))
    reading = AzureLayoutReader(client, 0.01).read_notice(b"%PDF", "application/pdf")
    assert reading.total_income_cents.value == 7517091
    model_id, body, kwargs = client.analyzed[0]
    assert (model_id, body, kwargs["content_type"]) == (
        "prebuilt-layout",
        b"%PDF",
        "application/pdf",
    )
    assert client.poller.timeout == 60


def test_read_notice_deletes_analyze_result_even_when_parsing_fails():
    bad = FakeResult({"pages": [{"lines": [{"content": "no spans"}]}]})
    client = FakeClient(FakePoller(bad))
    with pytest.raises(DocumentReadError):
        AzureLayoutReader(client, 0.01).read_notice(b"x", "application/pdf")
    assert client.deleted == [("prebuilt-layout", OPERATION_ID)]


def test_read_notice_deletes_analyze_result_when_the_poll_fails():
    client = FakeClient(FakePoller(HttpResponseError("boom")))
    with pytest.raises(DocumentReadError):
        AzureLayoutReader(client, 0.01).read_notice(b"x", "application/pdf")
    assert client.deleted == [("prebuilt-layout", OPERATION_ID)]


def test_read_notice_wraps_service_errors_in_document_read_error():
    client = FakeClient(HttpResponseError("boom"))
    with pytest.raises(DocumentReadError):
        AzureLayoutReader(client, 0.01).read_notice(b"x", "application/pdf")
    assert client.deleted == []  # no operation was created, so nothing to delete


def test_read_notice_treats_an_unfinished_operation_as_a_timeout():
    client = FakeClient(FakePoller(None, done=False))
    with pytest.raises(DocumentReadError, match="timed out"):
        AzureLayoutReader(client, 0.01).read_notice(b"x", "application/pdf")
    assert client.deleted == [("prebuilt-layout", OPERATION_ID)]


def test_read_notice_cost_counts_billed_pages():
    raw = {"pages": [{"pageNumber": 1}, {"pageNumber": 2}]}
    reader = AzureLayoutReader(FakeClient(FakePoller(FakeResult(raw))), 0.01)
    reader.read_notice(b"x", "application/pdf")
    assert reader.last_cost_usd == pytest.approx(0.02)


def test_read_notice_resets_cost_and_result_when_the_next_call_fails():
    client = FakeClient(FakePoller(fixture_result()))
    reader = AzureLayoutReader(client, 0.01)
    reader.read_notice(b"x", "application/pdf")
    assert reader.last_cost_usd > 0
    assert reader.last_result is not None
    client.poller = HttpResponseError("boom")
    with pytest.raises(DocumentReadError):
        reader.read_notice(b"x", "application/pdf")
    assert reader.last_cost_usd == 0.0
    assert reader.last_result is None


def test_read_notice_logs_a_failed_delete_without_hiding_the_reading(caplog):
    client = FakeClient(FakePoller(fixture_result()), delete_error=HttpResponseError("nope"))
    with caplog.at_level(logging.WARNING):
        reading = AzureLayoutReader(client, 0.01).read_notice(b"x", "application/pdf")
    assert reading.total_income_cents.value == 7517091
    assert [r.getMessage() for r in caplog.records] == [
        "azure_layout_delete_failed HttpResponseError"
    ]


def test_from_env_names_the_missing_variable_and_never_echoes_the_key(monkeypatch):
    monkeypatch.setenv("AZURE_DI_ENDPOINT", "https://example.cognitiveservices.azure.com/")
    monkeypatch.setenv("AZURE_DI_KEY", "secret-key-value")
    monkeypatch.delenv("AZURE_DI_PRICE_PER_PAGE_USD", raising=False)
    with pytest.raises(ValueError, match="AZURE_DI_PRICE_PER_PAGE_USD") as info:
        AzureLayoutReader.from_env()
    assert "secret-key-value" not in str(info.value)


def test_from_env_builds_a_reader_with_the_configured_price(monkeypatch):
    monkeypatch.setenv("AZURE_DI_ENDPOINT", "https://example.cognitiveservices.azure.com/")
    monkeypatch.setenv("AZURE_DI_KEY", "k")
    monkeypatch.setenv("AZURE_DI_PRICE_PER_PAGE_USD", "0.01")
    assert AzureLayoutReader.from_env().price_per_page_usd == 0.01
