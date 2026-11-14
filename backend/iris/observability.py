# AI contribution: 50% or more AI-generated
"""Privacy-conscious JSON events and a request identifier for Iris HTTP requests.

Auth success events include the user's UUID. Messages, credentials and other
personal details stay out of logs.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import UUID, uuid4

from django.http import HttpRequest, HttpResponseBase

_STANDARD_LOG_FIELDS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

_request_id: ContextVar[str | None] = ContextVar("iris_request_id", default=None)
_AUTH_USER_EVENTS = frozenset({"sign_in_succeeded", "signed_out"})
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
_PHOTO_REFERENCE = re.compile(r"listing-photos/[0-9a-f]{32}\.(?:jpg|png)")
_EXCEPTION_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
_REASON_CODES = frozenset(
    {"unhandled_exception", "smtp_error", "connection_error", "transport_error"}
)
_SESSION_CHECK_PATH = "/api/auth/browser/v1/auth/session"
_SESSION_REQUEST_LINE = re.compile(
    rf"GET {re.escape(_SESSION_CHECK_PATH)}(?:\?[^ ]*)? HTTP/1\.[01]"
)


def _add_diagnostic_fields(
    payload: dict[str, str | int], record: logging.LogRecord, event: str
) -> None:
    """Serialize exception types and registered codes, never free-form details."""
    exc_type = getattr(record, "exc_type", None)
    if exc_type is None and isinstance(record.exc_info, tuple) and record.exc_info:
        exc_type = record.exc_info[0]
    if (
        isinstance(exc_type, type)
        and issubclass(exc_type, BaseException)
        and _EXCEPTION_NAME.fullmatch(exc_type.__name__)
    ):
        payload["exc_type"] = exc_type.__name__
    reason = getattr(record, "reason", None)
    if (
        reason is None
        and record.name == "django.request"
        and event == "http_request_failed"
    ):
        reason = "unhandled_exception"
    if isinstance(reason, str) and reason in _REASON_CODES:
        payload["reason"] = reason


def _add_smtp_code(
    payload: dict[str, str | int], record: logging.LogRecord, event: str
) -> None:
    """Allow only an SMTP failure response code on the mail adapter's event."""
    code = getattr(record, "smtp_code", None)
    if (
        record.name == "iris.mailer"
        and event == "email_send_failed"
        and type(code) is int
        and 400 <= code <= 599
    ):
        payload["smtp_code"] = code


def _is_expected_session_check(request: object, status: object) -> bool:
    """Recognize only a signed-out browser GET session check."""
    return (
        isinstance(request, HttpRequest)
        and request.method == "GET"
        and request.path_info == _SESSION_CHECK_PATH
        and status == 401
    )


def _http_log_level(request: HttpRequest, status: int) -> int:
    """Keep expected session checks quiet without downgrading other failures."""
    if _is_expected_session_check(request, status):
        return logging.INFO
    if status >= 500:
        return logging.ERROR
    return logging.WARNING if status >= 400 else logging.INFO


def _is_expected_server_session_check(record: logging.LogRecord) -> bool:
    """Recognize runserver's transport record without serializing its raw URL."""
    return (
        record.name == "django.server"
        and getattr(record, "status_code", None) == 401
        and isinstance(record.args, tuple)
        and bool(record.args)
        and isinstance(record.args[0], str)
        and _SESSION_REQUEST_LINE.fullmatch(record.args[0]) is not None
    )


class ExpectedSessionCheckFilter(logging.Filter):
    """Apply the same session-check level to Django's separate request log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if _is_expected_server_session_check(record) or (
            record.name == "django.request"
            and _is_expected_session_check(
                getattr(record, "request", None), getattr(record, "status_code", None)
            )
        ):
            record.levelno = logging.INFO
            record.levelname = "INFO"
        return True


class QueueLogPrivacyFilter(logging.Filter):
    """Remove queue arguments before handlers can retain a library log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name == "procrastinate" or record.name.startswith("procrastinate."):
            for field in tuple(record.__dict__):
                if field not in _STANDARD_LOG_FIELDS:
                    del record.__dict__[field]
            record.msg = "background_job_event"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
            record.event = "background_job_event"
        return True


def _event_name(record: logging.LogRecord) -> str:
    """Return a safe event name."""
    default = (
        "http_request_failed"
        if record.name == "django.request"
        and record.levelno >= logging.ERROR
        and record.exc_info
        else "application_event"
    )
    event = getattr(record, "event", default)
    if isinstance(event, str) and event.replace("_", "").isalnum():
        return event
    return "application_event"


def _add_auth_user(
    payload: dict[str, str | int], record: logging.LogRecord, event: str
) -> None:
    """Add the account UUID only for successful authentication events."""
    user_id = getattr(record, "user_id", None)
    if (
        record.name == "iris.auth"
        and event in _AUTH_USER_EVENTS
        and isinstance(user_id, UUID)
    ):
        payload["user_id"] = str(user_id)


def _add_request_fields(
    payload: dict[str, str | int], record: logging.LogRecord
) -> None:
    """Add allowlisted HTTP request fields."""
    method = getattr(record, "method", None)
    if isinstance(method, str) and method in _HTTP_METHODS:
        payload["method"] = method

    route = getattr(record, "route", None)
    if isinstance(route, str):
        payload["route"] = route

    for field in ("status_code", "duration_ms"):
        value = getattr(record, field, None)
        if isinstance(value, int):
            payload[field] = value


def _add_photo_reference(
    payload: dict[str, str | int], record: logging.LogRecord, event: str
) -> None:
    """Add an opaque orphan-photo reference only for cleanup failures."""
    photo_ref = getattr(record, "photo_ref", None)
    if (
        record.name == "iris.listings"
        and event == "listing_photo_cleanup_failed"
        and isinstance(photo_ref, str)
        and _PHOTO_REFERENCE.fullmatch(photo_ref)
    ):
        payload["photo_ref"] = photo_ref


def _add_eligibility_fields(
    payload: dict[str, str | int], record: logging.LogRecord, event: str
) -> None:
    """Allow only opaque decision references, a fixed outcome and rule version."""
    if record.name != "iris.eligibility" or event != "eligibility_decided":
        return

    for field in ("decision_id", "household_id"):
        value = getattr(record, field, None)
        if isinstance(value, UUID):
            payload[field] = str(value)

    outcome = getattr(record, "outcome", None)
    if isinstance(outcome, str) and outcome in {"eligible", "ineligible"}:
        payload["outcome"] = outcome

    rule_version = getattr(record, "rule_version", None)
    if type(rule_version) is int and rule_version > 0:
        payload["rule_version"] = rule_version


def _add_partner_application(
    payload: dict[str, str | int], record: logging.LogRecord, event: str
) -> None:
    """Permit an opaque recovery reference only on the stores email-failure event."""
    if (
        record.name != "iris.stores"
        or event != "partner_application_decision_email_failed"
    ):
        return
    try:
        application_id = UUID(str(getattr(record, "application_id", "")))
    except ValueError:
        # Invalid diagnostic fields are discarded without recursive logging.
        return
    payload["application_id"] = str(application_id)


class JsonLogFormatter(logging.Formatter):
    """Serialize an allowlist of fields instead of arbitrary log message text."""

    def format(self, record: logging.LogRecord) -> str:
        """Return one privacy-filtered JSON event."""
        event = _event_name(record)
        payload: dict[str, str | int] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": event,
        }
        request_id = _request_id.get()
        if request_id:
            payload["request_id"] = request_id

        _add_diagnostic_fields(payload, record, event)
        _add_auth_user(payload, record, event)
        _add_request_fields(payload, record)
        _add_photo_reference(payload, record, event)
        _add_smtp_code(payload, record, event)
        _add_eligibility_fields(payload, record, event)
        _add_partner_application(payload, record, event)
        return json.dumps(payload, separators=(",", ":"))


class RequestIdMiddleware:
    """Attach a server-generated X-Request-ID and log safe request metrics."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        """Attach a request ID and log safe request metrics."""
        request_id = uuid4().hex
        token = _request_id.set(request_id)
        request.iris_request_id = request_id  # type: ignore[attr-defined]
        started_at = time.perf_counter()
        logger = logging.getLogger("iris.http")

        try:
            try:
                response = self.get_response(request)
            except Exception as exc:
                logger.error(
                    "HTTP request failed",
                    extra={
                        "event": "http_request_failed",
                        "exc_type": type(exc),
                        "reason": "unhandled_exception",
                    },
                )
                raise

            match = getattr(request, "resolver_match", None)
            route = getattr(match, "route", "unmatched")
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            status = response.status_code
            logger.log(
                _http_log_level(request, status),
                "HTTP request completed",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "route": route,
                    "status_code": status,
                    "duration_ms": duration_ms,
                },
            )
            response["X-Request-ID"] = request_id
            return response
        finally:
            _request_id.reset(token)
