# AI contribution: 50% or more AI-generated
"""Privacy-conscious JSON events and a request identifier for Iris HTTP requests.

Logs deliberately do not serialize message text, URLs, query strings, headers,
request bodies, account identifiers, or exception details.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import uuid4

from django.http import HttpRequest, HttpResponseBase

_request_id: ContextVar[str | None] = ContextVar("iris_request_id", default=None)


class JsonLogFormatter(logging.Formatter):
    """Serialize an allowlist of fields instead of arbitrary log message text."""

    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", "application_event")
        if not isinstance(event, str) or not event.replace("_", "").isalnum():
            event = "application_event"

        payload: dict[str, str | int] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": event,
        }
        request_id = _request_id.get()
        if request_id:
            payload["request_id"] = request_id

        for field in ("method", "route", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if field == "method" and value in {
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "HEAD",
                "OPTIONS",
            }:
                payload[field] = value
            elif field == "route" and isinstance(value, str):
                # Route is the matched *pattern*, never the requested path or query.
                payload[field] = value
            elif field in {"status_code", "duration_ms"} and isinstance(value, int):
                payload[field] = value

        return json.dumps(payload, separators=(",", ":"))


class RequestIdMiddleware:
    """Attach a server-generated X-Request-ID and log safe request metrics."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponseBase]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
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
