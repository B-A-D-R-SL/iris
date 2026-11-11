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

_request_id: ContextVar[str | None] = ContextVar("iris_request_id", default=None)
_AUTH_USER_EVENTS = frozenset({"sign_in_succeeded", "signed_out"})
_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
_PHOTO_REFERENCE = re.compile(r"listing-photos/[0-9a-f]{32}\.(?:jpg|png)")


def _event_name(record: logging.LogRecord) -> str:
    """Return a safe event name."""
    event = getattr(record, "event", "application_event")
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

        _add_auth_user(payload, record, event)
        _add_request_fields(payload, record)
        _add_photo_reference(payload, record, event)
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
            except Exception:
                logger.error(
                    "HTTP request failed", extra={"event": "http_request_failed"}
                )
                raise

            match = getattr(request, "resolver_match", None)
            route = getattr(match, "route", "unmatched")
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            status = response.status_code
            level = (
                logging.ERROR
                if status >= 500
                else logging.WARNING
                if status >= 400
                else logging.INFO
            )
            logger.log(
                level,
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
