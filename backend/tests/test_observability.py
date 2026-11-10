# AI contribution: 50% or more AI-generated
"""Tests for structured HTTP logging, privacy filtering, and auth routing."""

import json
import logging
from io import StringIO
from uuid import UUID

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import Client
from django.urls import get_resolver

from iris.observability import JsonLogFormatter, RequestIdMiddleware


def test_health_response_has_server_generated_request_id(client: Client) -> None:
    response = client.get("/api/health/", HTTP_X_REQUEST_ID="not-trusted")
    assert response.status_code == 200
    request_id = response["X-Request-ID"]
    assert UUID(hex=request_id).hex == request_id
    assert request_id != "not-trusted"


def test_request_logging_does_not_expose_query_or_header(client: Client) -> None:
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("iris.http")
    logger.addHandler(handler)
    try:
        response = client.get(
            "/api/health/?email=private@example.org",
            HTTP_AUTHORIZATION="Bearer secret-token",
        )
    finally:
        logger.removeHandler(handler)
        handler.close()

    events = [json.loads(line) for line in output.getvalue().splitlines()]
    event = next(item for item in events if item["event"] == "http_request")
    assert event["level"] == "INFO"
    assert event["method"] == "GET"
    assert event["status_code"] == 200
    assert event["request_id"] == response["X-Request-ID"]
    assert "private@example.org" not in output.getvalue()
    assert "secret-token" not in output.getvalue()


def test_formatter_discards_arbitrary_message_and_exceptions() -> None:
    record = logging.LogRecord(
        name="some.library",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Personal data: private@example.org",
        args=(),
        exc_info=None,
    )
    record.event = "safe_failure"
    encoded = JsonLogFormatter().format(record)
    assert json.loads(encoded)["event"] == "safe_failure"
    assert "private@example.org" not in encoded


@pytest.mark.parametrize(
    ("logger_name", "event", "reference", "included"),
    [
        (
            "iris.listings",
            "listing_photo_cleanup_failed",
            "listing-photos/" + "a" * 32 + ".jpg",
            True,
        ),
        (
            "iris.listings",
            "listing_photo_cleanup_failed",
            "listing-photos/" + "b" * 32 + ".png",
            True,
        ),
        (
            "iris.http",
            "listing_photo_cleanup_failed",
            "listing-photos/" + "a" * 32 + ".jpg",
            False,
        ),
        (
            "iris.listings",
            "listing_photo_read_failed",
            "listing-photos/" + "a" * 32 + ".jpg",
            False,
        ),
        (
            "iris.listings",
            "listing_photo_cleanup_failed",
            "https://storage.example.test/photo?sig=secret",
            False,
        ),
        ("iris.listings", "listing_photo_cleanup_failed", "../private", False),
        ("iris.listings", "listing_photo_cleanup_failed", None, False),
    ],
)
def test_formatter_limits_orphan_references_to_valid_cleanup_events(
    logger_name: str, event: str, reference: str | None, included: bool
) -> None:
    """Only opaque server photo names reach cleanup logs; URLs and other events do not."""
    record = logging.LogRecord(
        logger_name, logging.ERROR, __file__, 1, "private text", (), None
    )
    record.event = event
    record.photo_ref = reference
    encoded = JsonLogFormatter().format(record)
    payload = json.loads(encoded)
    assert ("photo_ref" in payload) is included
    if included:
        assert payload["photo_ref"] == reference
    assert "secret" not in encoded
    assert "private text" not in encoded


def test_headless_auth_routes_are_mounted_under_api_auth() -> None:
    routes = [str(pattern.pattern) for pattern in get_resolver().url_patterns]
    assert "api/auth/" in routes
    assert "_allauth/" not in routes


def test_http_request_uses_warning_and_error_levels() -> None:
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonLogFormatter())
    logger = logging.getLogger("iris.http")
    logger.addHandler(handler)
    try:
        for code in (404, 503):
            request = HttpRequest()
            request.method = "GET"

            def respond(_request: HttpRequest, status: int = code) -> HttpResponse:
                return HttpResponse(status=status)

            response = RequestIdMiddleware(respond)(request)
            assert response.status_code == code
    finally:
        logger.removeHandler(handler)
        handler.close()

    events = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [event["level"] for event in events] == ["WARNING", "ERROR"]
    assert [event["status_code"] for event in events] == [404, 503]
