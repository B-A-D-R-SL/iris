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


@pytest.mark.parametrize("event", ["sign_in_succeeded", "signed_out"])
def test_auth_success_logs_only_uuid_as_account_detail(event):
    """Successful authentication logs expose only the account UUID."""
    user_id = UUID("00000000-0000-4000-8000-000000000011")
    record = logging.makeLogRecord(
        {
            "name": "iris.auth",
            "levelname": "INFO",
            "event": event,
            "user_id": user_id,
            "email": "private@example.test",
            "password": "private-password",
            "msg": "private@example.test",
        }
    )
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload == {
        "timestamp": payload["timestamp"],
        "level": "INFO",
        "logger": "iris.auth",
        "event": event,
        "user_id": str(user_id),
    }


@pytest.mark.parametrize(
    ("logger", "event", "user_id"),
    [
        ("iris.auth", "sign_in_failed", UUID(int=11)),
        ("iris.auth", "sign_in_rate_limited", UUID(int=11)),
        ("iris.http", "sign_in_succeeded", UUID(int=11)),
        ("iris.auth", "signed_out", "private@example.test"),
    ],
)
def test_other_events_cannot_expose_account_details(logger, event, user_id):
    """Other log events cannot expose account identifiers."""
    record = logging.makeLogRecord({"name": logger, "event": event, "user_id": user_id})
    assert "user_id" not in json.loads(JsonLogFormatter().format(record))


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


@pytest.mark.parametrize("outcome", ["eligible", "ineligible"])
def test_eligibility_event_discards_personal_and_financial_details(outcome):
    record = logging.makeLogRecord(
        {
            "name": "iris.eligibility",
            "levelname": "INFO",
            "event": "eligibility_decided",
            "decision_id": UUID(int=12),
            "household_id": UUID(int=13),
            "outcome": outcome,
            "rule_version": 2,
            "adult_incomes_cents": [12_345, 20_000],
            "household_income_cents": 32_345,
            "threshold_cents": 36_527,
            "name_of_holder": "Private Person",
            "email": "private@example.test",
            "msg": "Private Person earns 32345",
        }
    )

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload == {
        "timestamp": payload["timestamp"],
        "level": "INFO",
        "logger": "iris.eligibility",
        "event": "eligibility_decided",
        "decision_id": str(UUID(int=12)),
        "household_id": str(UUID(int=13)),
        "outcome": outcome,
        "rule_version": 2,
    }


@pytest.mark.parametrize(
    ("logger_name", "event"),
    [("iris.http", "eligibility_decided"), ("iris.eligibility", "decision_failed")],
)
def test_other_events_cannot_expose_eligibility_fields(logger_name, event):
    record = logging.makeLogRecord(
        {
            "name": logger_name,
            "event": event,
            "decision_id": UUID(int=12),
            "household_id": UUID(int=13),
            "outcome": "eligible",
            "rule_version": 2,
        }
    )

    payload = json.loads(JsonLogFormatter().format(record))

    assert set(payload) == {"timestamp", "level", "logger", "event"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("decision_id", "private@example.test"),
        ("household_id", "Private Person"),
        ("outcome", "Private Person is eligible"),
        ("outcome", ["eligible"]),
        ("rule_version", "private@example.test"),
        ("rule_version", True),
        ("rule_version", 0),
    ],
)
def test_eligibility_fields_reject_values_outside_the_allowlist(field, value):
    record = logging.makeLogRecord(
        {"name": "iris.eligibility", "event": "eligibility_decided", field: value}
    )

    payload = json.loads(JsonLogFormatter().format(record))

    assert set(payload) == {"timestamp", "level", "logger", "event"}
