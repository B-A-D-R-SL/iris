# AI contribution: 50% or more AI-generated
"""VlmReader against a fake google-genai client (no cloud calls)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from conftest import make_row
from google.genai import errors

from reader import UNREAD, ConfiguredReader, DocumentReadError
from run import READERS
from score import score_reading
from vlm_reader import SYSTEM_PROMPT, VlmReader, parse_vlm_json, to_images

NOTICES = Path(__file__).resolve().parents[3] / "mock-data" / "notices"
PNG = b"\x89PNG\r\n\x1a\n"
JPEG = b"\xff\xd8\xff\xe0"


def payload(**overrides: dict) -> dict:
    values = {
        "full_name": {"text": "Zoé Jessica Lapointe", "confidence": 0.99},
        "street_number": {"text": "1924", "confidence": 0.98},
        "street_name": {"text": "boulevard Saint-Laurent", "confidence": 0.98},
        "unit": {"text": "", "confidence": 0.9},
        "postal_code": {"text": "H2X 4N1", "confidence": 0.97},
        "tax_year": {"text": "2025", "confidence": 0.99},
        "total_income": {"text": "75 170,91", "confidence": 0.97},
        "notice_date": {"text": "28 mars 2026", "confidence": 0.96},
    }
    values.update(overrides)
    return values


class FakeModels:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


class FakeClient:
    def __init__(self, outcome):
        self.models = FakeModels(outcome)


def response(body: dict | str, prompt=1000, candidates=200, thoughts=50) -> SimpleNamespace:
    text = body if isinstance(body, str) else json.dumps(body)
    usage = SimpleNamespace(
        prompt_token_count=prompt,
        candidates_token_count=candidates,
        thoughts_token_count=thoughts,
    )
    return SimpleNamespace(text=text, usage_metadata=usage)


def test_to_images_renders_both_pdf_pages_as_png():
    images = to_images((NOTICES / "pdf" / "notice-001.pdf").read_bytes(), "application/pdf")
    assert len(images) == 2
    assert all(image.startswith(PNG) for image in images)


def test_to_images_passes_photos_through():
    assert to_images(PNG + b"x", "image/png") == [PNG + b"x"]
    assert to_images(JPEG, "image/jpeg") == [JPEG]


def test_to_images_rejects_other_content_types():
    with pytest.raises(ValueError, match="unsupported"):
        to_images(b"GIF89a", "image/gif")


def test_parse_vlm_json_converts_printed_text_to_typed_fields():
    reading = parse_vlm_json(payload())
    assert reading.total_income_cents.value == 7517091
    assert reading.total_income_cents.confidence == 0.97
    assert reading.notice_date.value == dt.date(2026, 3, 28)
    assert reading.tax_year.value == 2025
    assert reading.postal_code.value == "H2X 4N1"
    assert reading.full_name.value == "Zoé Jessica Lapointe"
    assert reading.unit.value == ""


def test_parse_vlm_json_drops_the_unit_marker_like_the_layout_parser():
    reading = parse_vlm_json(payload(unit={"text": "app. 106", "confidence": 0.95}))
    assert reading.unit.value == "106"  # truth.csv stores 106; the notice prints "app. 106"
    assert reading.unit.confidence == 0.95


def test_read_notice_scores_a_printed_unit_as_correct():
    body = payload(unit={"text": "app. 106", "confidence": 0.95})
    reading = VlmReader(FakeClient(response(body)), "m", 1.0, 1.0).read_notice(PNG, "image/png")
    assert score_reading(make_row(unit="106"), reading).outcomes["unit"] == "correct"


def test_parse_vlm_json_unparseable_amount_becomes_unread_field():
    reading = parse_vlm_json(payload(total_income={"text": "beaucoup", "confidence": 0.99}))
    assert reading.total_income_cents == UNREAD


def test_parse_vlm_json_null_text_and_bad_year_become_unread():
    reading = parse_vlm_json(
        payload(
            full_name={"text": None, "confidence": 0.0},
            tax_year={"text": "20255", "confidence": 0.9},
        )
    )
    assert reading.full_name == UNREAD
    assert reading.tax_year == UNREAD


def test_parse_vlm_json_missing_field_raises_document_read_error():
    body = payload()
    del body["notice_date"]
    with pytest.raises(DocumentReadError):
        parse_vlm_json(body)


def test_parse_vlm_json_extra_field_raises_document_read_error():
    body = payload(notice_number={"text": "Q1234567890", "confidence": 0.9})
    with pytest.raises(DocumentReadError) as info:
        parse_vlm_json(body)
    assert "Q1234567890" not in str(info.value)


def test_parse_vlm_json_confidence_out_of_range_raises_document_read_error():
    with pytest.raises(DocumentReadError):
        parse_vlm_json(payload(total_income={"text": "75 170,91", "confidence": 1.4}))


@pytest.mark.parametrize(
    "bad",
    [
        "75 170,91",
        {"text": 7517091, "confidence": 0.9},
        {"text": "1", "confidence": "high"},
        {"text": "1", "confidence": True},
        {"text": "1"},
    ],
)
def test_parse_vlm_json_malformed_value_raises_document_read_error(bad):
    with pytest.raises(DocumentReadError):
        parse_vlm_json(payload(total_income=bad))


def test_read_notice_sends_images_and_computes_cost_from_usage():
    client = FakeClient(response(payload()))
    reader = VlmReader(client, "gemini-test", 1.0, 4.0)
    reading = reader.read_notice(PNG + b"x", "image/png")
    assert reading.total_income_cents.value == 7517091
    call = client.models.calls[0]
    assert call["model"] == "gemini-test"
    image_part = call["contents"][0]
    assert image_part.inline_data.data == PNG + b"x"
    assert image_part.inline_data.mime_type == "image/png"
    config = call["config"]
    assert config.system_instruction == SYSTEM_PROMPT
    assert config.temperature is None
    assert config.response_mime_type == "application/json"
    assert config.http_options.timeout == 60_000
    assert not config.tools
    # 1000 input tokens at 1 USD/M plus (200 + 50 thinking) output tokens at 4 USD/M
    assert reader.last_cost_usd == pytest.approx(1000 * 1.0 / 1e6 + 250 * 4.0 / 1e6)


def test_read_notice_renders_pdf_pages_as_png_parts():
    client = FakeClient(response(payload()))
    pdf = (NOTICES / "pdf" / "notice-001.pdf").read_bytes()
    VlmReader(client, "m", 1.0, 1.0).read_notice(pdf, "application/pdf")
    parts = [p for p in client.models.calls[0]["contents"] if not isinstance(p, str)]
    assert len(parts) == 2
    assert all(p.inline_data.mime_type == "image/png" for p in parts)


@pytest.mark.parametrize(
    "error",
    [
        errors.ServerError(503, {"error": {"message": "down", "status": "UNAVAILABLE"}}),
        errors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}}),
        httpx.ReadTimeout("slow"),
        httpx.ConnectError("no route"),
    ],
)
def test_read_notice_wraps_sdk_errors_in_document_read_error(error):
    reader = VlmReader(FakeClient(error), "m", 1.0, 1.0)
    with pytest.raises(DocumentReadError, match=type(error).__name__):
        reader.read_notice(PNG, "image/png")


@pytest.mark.parametrize("text", ["not json", "[1, 2]", None])
def test_read_notice_wraps_invalid_json_in_document_read_error(text):
    reply = response("")
    reply.text = text
    reader = VlmReader(FakeClient(reply), "m", 1.0, 1.0)
    with pytest.raises(DocumentReadError):
        reader.read_notice(PNG, "image/png")


def test_read_notice_rejects_an_unsupported_content_type_as_document_read_error():
    reader = VlmReader(FakeClient(response(payload())), "m", 1.0, 1.0)
    with pytest.raises(DocumentReadError):
        reader.read_notice(b"x", "image/gif")


def test_read_notice_resets_cost_when_the_next_call_fails():
    client = FakeClient(response(payload()))
    reader = VlmReader(client, "m", 1.0, 1.0)
    reader.read_notice(PNG, "image/png")
    assert reader.last_cost_usd > 0
    client.models.outcome = httpx.ReadTimeout("slow")
    with pytest.raises(DocumentReadError):
        reader.read_notice(PNG, "image/png")
    assert reader.last_cost_usd == 0.0


def test_read_notice_cost_is_zero_when_usage_is_missing():
    reply = response(payload())
    reply.usage_metadata = None
    reader = VlmReader(FakeClient(reply), "m", 1.0, 1.0)
    reader.read_notice(PNG, "image/png")
    assert reader.last_cost_usd == 0.0


def test_settings_record_model_region_temperature_and_thinking():
    reader = VlmReader(FakeClient(response(payload())), "gemini-test", 0.3, 2.5)
    assert isinstance(reader, ConfiguredReader)
    assert reader.settings == {
        "model": "gemini-test",
        "region": "northamerica-northeast1",
        "temperature": "model default (not set by the reader)",
        "thinking": "model default (not set by the reader)",
    }


def test_read_notice_sends_no_sampling_or_thinking_setting_as_its_settings_report():
    """Google: temperature, top_p and top_k are no longer recommended for Gemini 3.x."""
    client = FakeClient(response(payload()))
    reader = VlmReader(client, "m", 1.0, 1.0)
    reader.read_notice(PNG, "image/png")
    config = client.models.calls[0]["config"]
    assert (config.temperature, config.top_p, config.top_k) == (None, None, None)
    assert config.thinking_config is None
    assert (
        reader.settings["temperature"]
        == reader.settings["thinking"]
        == ("model default (not set by the reader)")
    )


def _env(monkeypatch, **overrides: str | None) -> None:
    values = {
        "GOOGLE_CLOUD_PROJECT": "iris-spike",
        "VERTEX_MODEL": "gemini-test",
        "VERTEX_LOCATION": "northamerica-northeast1",
        "VERTEX_INPUT_PRICE_PER_MTOK_USD": "0.30",
        "VERTEX_OUTPUT_PRICE_PER_MTOK_USD": "2.50",
    }
    values.update(overrides)
    for name, value in values.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def test_from_env_refuses_a_location_other_than_montreal(monkeypatch):
    _env(monkeypatch, VERTEX_LOCATION="us-central1")
    with pytest.raises(ValueError, match="northamerica-northeast1"):
        VlmReader.from_env()


def test_from_env_names_the_missing_variable(monkeypatch):
    _env(monkeypatch, VERTEX_MODEL=None)
    with pytest.raises(ValueError, match="VERTEX_MODEL"):
        VlmReader.from_env()


def test_from_env_rejects_a_price_that_is_not_a_number(monkeypatch):
    _env(monkeypatch, VERTEX_INPUT_PRICE_PER_MTOK_USD="cheap")
    with pytest.raises(ValueError, match="VERTEX_INPUT_PRICE_PER_MTOK_USD"):
        VlmReader.from_env()


def test_from_env_builds_a_vertex_client_in_montreal(monkeypatch):
    _env(monkeypatch)
    seen: dict = {}

    def fake_client(**kwargs):
        seen.update(kwargs)
        return FakeClient(response(payload()))

    monkeypatch.setattr("vlm_reader.genai.Client", fake_client)
    reader = VlmReader.from_env()
    assert seen == {
        "vertexai": True,
        "project": "iris-spike",
        "location": "northamerica-northeast1",
    }
    assert (reader.model, reader.input_price_per_mtok, reader.output_price_per_mtok) == (
        "gemini-test",
        0.30,
        2.50,
    )


def test_vlm_is_registered_in_the_reader_registry():
    assert READERS["vlm"] == VlmReader.from_env
