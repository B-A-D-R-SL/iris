# AI contribution: 50% or more AI-generated
"""Failure diagnostics retain useful codes while discarding personal details."""

import json
import logging
import sys
from io import StringIO

import pytest
from django.core.servers.basehttp import WSGIRequestHandler
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import path

from iris.observability import (
    ExpectedSessionCheckFilter,
    JsonLogFormatter,
    RequestIdMiddleware,
)

SESSION = "/api/auth/browser/v1/auth/session"
PRIVATE = "private@example.test secret-subject secret-body"


def _payload(**extra):
    record = logging.makeLogRecord(
        {"name": "iris.test", "levelname": "ERROR", "msg": PRIVATE, **extra}
    )
    return json.loads(JsonLogFormatter().format(record))


@pytest.fixture
def request_logs():
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonLogFormatter())
    loggers = [
        logging.getLogger(name)
        for name in ("iris.http", "django.request", "django.server")
    ]
    for logger in loggers:
        logger.addHandler(handler)
    try:
        yield output
    finally:
        for logger in loggers:
            logger.removeHandler(handler)
        handler.close()


def _failing_view(request):
    raise ValueError(PRIVATE)


urlpatterns = [path("failure/", _failing_view)]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("exc_type", ValueError, "ValueError"),
        ("exc_type", TimeoutError, "TimeoutError"),
        ("reason", "smtp_error", "smtp_error"),
        ("reason", "connection_error", "connection_error"),
        ("reason", "unhandled_exception", "unhandled_exception"),
        ("reason", "transport_error", "transport_error"),
    ],
)
def test_formatter_allows_only_the_safe_diagnostic_value(field, value, expected):
    payload = _payload(**{field: value}, email=PRIVATE, subject=PRIVATE)
    assert payload == {
        "timestamp": payload["timestamp"],
        "level": "ERROR",
        "logger": "iris.test",
        "event": "application_event",
        field: expected,
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exc_type", PRIVATE),
        ("exc_type", "ValueError"),
        ("exc_type", ValueError(PRIVATE)),
        ("exc_type", str),
        ("exc_type", type(PRIVATE, (Exception,), {})),
        ("reason", PRIVATE),
        ("reason", "PRIVATE_PERSON"),
        ("reason", "unregistered_code"),
        ("reason", ["smtp_error"]),
        ("reason", None),
    ],
)
def test_formatter_rejects_untrusted_diagnostic_values(field, value):
    payload = _payload(**{field: value})
    assert set(payload) == {"timestamp", "level", "logger", "event"}


def test_exception_info_exposes_only_its_class():
    try:
        raise ConnectionError(PRIVATE)
    except ConnectionError:
        payload = _payload(exc_info=sys.exc_info())
    assert payload["exc_type"] == "ConnectionError"
    assert set(payload) == {"timestamp", "level", "logger", "event", "exc_type"}
    assert PRIVATE not in json.dumps(payload)


def test_middleware_logs_and_reraises_an_unhandled_failure(request_logs):
    request = RequestFactory().get("/failure/?email=private@example.test")
    error = ValueError(PRIVATE)

    def fail(_request):
        raise error

    with pytest.raises(ValueError) as raised:
        RequestIdMiddleware(fail)(request)

    assert raised.value is error
    [event] = [json.loads(line) for line in request_logs.getvalue().splitlines()]
    assert event["event"] == "http_request_failed"
    assert event["level"] == "ERROR"
    assert event["exc_type"] == "ValueError"
    assert event["reason"] == "unhandled_exception"
    assert event["request_id"] == request.iris_request_id
    assert PRIVATE not in request_logs.getvalue()
    assert "request_id" not in _payload()


@pytest.mark.parametrize(
    ("method", "url", "status", "level"),
    [
        ("GET", SESSION, 401, "INFO"),
        ("GET", SESSION + "?email=private@example.test", 401, "INFO"),
        ("DELETE", SESSION, 401, "WARNING"),
        ("HEAD", SESSION, 401, "WARNING"),
        ("GET", SESSION + "/", 401, "WARNING"),
        ("GET", "/api/auth/app/v1/auth/session", 401, "WARNING"),
        ("GET", "/api/other/", 401, "WARNING"),
        ("GET", SESSION, 403, "WARNING"),
        ("GET", SESSION, 500, "ERROR"),
        ("GET", "/api/health/", 200, "INFO"),
    ],
)
def test_only_expected_session_401_is_downgraded(
    request_logs, method, url, status, level
):
    request = RequestFactory().generic(method, url)
    response = RequestIdMiddleware(lambda _: HttpResponse(status=status))(request)
    [event] = [json.loads(line) for line in request_logs.getvalue().splitlines()]
    assert event["level"] == level
    assert event["status_code"] == status
    assert event["request_id"] == response["X-Request-ID"]
    assert "private@example.test" not in request_logs.getvalue()


@pytest.mark.django_db
def test_real_signed_out_session_logs_info_in_both_request_loggers(
    client, request_logs
):
    response = client.get(SESSION)
    assert response.status_code == 401
    events = [json.loads(line) for line in request_logs.getvalue().splitlines()]
    assert {event["logger"] for event in events} == {"iris.http", "django.request"}
    assert all(event["level"] == "INFO" for event in events)


@override_settings(ROOT_URLCONF=__name__)
def test_django_caught_failure_still_has_exception_type(client, request_logs):
    client.raise_request_exception = False
    response = client.get("/failure/?email=private@example.test")
    assert response.status_code == 500
    events = [json.loads(line) for line in request_logs.getvalue().splitlines()]
    [failure] = [event for event in events if event["event"] == "http_request_failed"]
    assert failure["logger"] == "django.request"
    assert failure["level"] == "ERROR"
    assert failure["exc_type"] == "ValueError"
    assert failure["reason"] == "unhandled_exception"
    assert failure["request_id"] == response["X-Request-ID"]
    assert "private@example.test" not in request_logs.getvalue()
    assert "secret-subject" not in request_logs.getvalue()


@pytest.mark.parametrize(
    ("logger", "method", "url", "status", "expected"),
    [
        ("django.request", "GET", SESSION, 401, logging.INFO),
        ("django.request", "DELETE", SESSION, 401, logging.WARNING),
        ("django.request", "GET", "/api/other/", 401, logging.WARNING),
        ("django.request", "GET", SESSION, 403, logging.WARNING),
        ("django.security", "GET", SESSION, 401, logging.WARNING),
    ],
)
def test_framework_filter_keeps_unrelated_warnings(
    logger, method, url, status, expected
):
    record = logging.makeLogRecord(
        {
            "name": logger,
            "levelno": logging.WARNING,
            "levelname": "WARNING",
            "request": RequestFactory().generic(method, url),
            "status_code": status,
        }
    )
    assert ExpectedSessionCheckFilter().filter(record) is True
    assert record.levelno == expected
    assert record.levelname == logging.getLevelName(expected)


@pytest.mark.parametrize(
    ("request_line", "status", "level"),
    [
        (f"GET {SESSION} HTTP/1.1", "401", "INFO"),
        (f"GET {SESSION}?email=private@example.test HTTP/1.1", "401", "INFO"),
        (f"DELETE {SESSION} HTTP/1.1", "401", "WARNING"),
        ("GET /api/other/ HTTP/1.1", "401", "WARNING"),
        (f"GET {SESSION} HTTP/1.1", "403", "WARNING"),
        (f"GET {SESSION} HTTP/1.1", "500", "ERROR"),
    ],
)
def test_runserver_does_not_add_a_duplicate_session_warning(
    request_logs, monkeypatch, request_line, status, level
):
    handler = WSGIRequestHandler.__new__(WSGIRequestHandler)
    handler.request = None
    monkeypatch.setattr(handler, "log_date_time_string", lambda: "test-time")
    handler.log_message('"%s" %s %s', request_line, status, "0")
    [event] = [json.loads(line) for line in request_logs.getvalue().splitlines()]
    assert event["logger"] == "django.server"
    assert event["level"] == level
    assert event["status_code"] == int(status)
    assert "private@example.test" not in request_logs.getvalue()
    assert "HTTP/1.1" not in request_logs.getvalue()


@pytest.mark.parametrize("code", [451, 554])
def test_smtp_failure_response_code_is_an_integer_only(code):
    payload = _payload(name="iris.mailer", event="email_send_failed", smtp_code=code)
    assert payload == {
        "timestamp": payload["timestamp"],
        "level": "ERROR",
        "logger": "iris.mailer",
        "event": "email_send_failed",
        "smtp_code": code,
    }


@pytest.mark.parametrize(
    ("logger", "event", "code"),
    [
        ("iris.mailer", "email_send_failed", True),
        ("iris.mailer", "email_send_failed", "451"),
        ("iris.mailer", "email_send_failed", PRIVATE),
        ("iris.mailer", "email_send_failed", None),
        ("iris.mailer", "email_send_failed", 399),
        ("iris.mailer", "email_send_failed", 600),
        ("iris.notifications", "email_send_failed", 451),
        ("iris.mailer", "email_sent", 451),
    ],
)
def test_smtp_codes_cannot_leak_text_or_escape_the_mail_adapter_event(
    logger, event, code
):
    payload = _payload(name=logger, event=event, smtp_code=code)
    assert set(payload) == {"timestamp", "level", "logger", "event"}
