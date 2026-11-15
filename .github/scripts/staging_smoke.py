# AI contribution: 50% or more AI-generated
"""Verify the new release, worker/DB readiness, SPA deep links and static assets."""

import json
import logging
import re
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


def _get(url: str, *, deadline: float) -> bytes:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Staging startup deadline expired.")
    headers = {"Cache-Control": "no-cache"}
    # Local release tests emulate App Service's trusted TLS terminator only on loopback.
    if url.startswith(("http://localhost:", "http://127.0.0.1:")):
        headers["X-Forwarded-Proto"] = "https"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=min(10, remaining)) as response:
        return response.read()


def _verify_release(origin: str, revision: str, deadline: float) -> None:
    """Verify the requested revision and every referenced built asset."""
    payload = json.loads(_get(f"{origin}/api/ready/", deadline=deadline))
    if payload != {"status": "ok", "revision": revision}:
        raise ValueError("New release is not ready.")
    html = _get(f"{origin}/sign-in", deadline=deadline).decode()
    assets = re.findall(
        r"(?:src|href)=[\"\'](/assets/[^\"\'<>]+\.(?:js|css))[\"\']", html
    )
    if not assets or any(
        not _get(f"{origin}{asset}", deadline=deadline) for asset in assets
    ):
        raise ValueError("Built frontend is unavailable.")
    if not _get(f"{origin}/static/admin/css/base.css", deadline=deadline):
        raise ValueError("Collected admin assets are unavailable.")


def smoke(
    origin: str, revision: str, attempts: int | None = None, *, timeout: float = 600
) -> None:
    """Allow the documented startup window; old replicas cannot satisfy readiness."""
    if timeout <= 0 or (attempts is not None and attempts < 1):
        raise ValueError("A positive startup window and attempt limit are required.")
    deadline = time.monotonic() + timeout
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            _verify_release(origin, revision, deadline)
            if time.monotonic() > deadline:
                raise TimeoutError("Staging startup deadline expired.")
            return
        except (URLError, OSError, ValueError) as error:
            logger.warning(
                "Staging smoke attempt %d failed (%s).",
                attempt,
                type(error).__name__,
                extra={
                    "event": "staging_smoke_attempt_failed",
                    "attempt": attempt,
                    "error_type": type(error).__name__,
                },
            )
            remaining = deadline - time.monotonic()
            if remaining <= 0 or (attempts is not None and attempt >= attempts):
                raise RuntimeError("Staging release smoke check failed.") from None
            time.sleep(min(5, remaining))
    logger.error(
        "Staging smoke startup deadline expired.",
        extra={
            "event": "staging_smoke_failed",
            "attempt": attempt,
            "error_type": "TimeoutError",
        },
    )
    raise RuntimeError("Staging release smoke check failed.")


if __name__ == "__main__":
    logging.basicConfig(format="%(message)s")
    smoke(sys.argv[1].rstrip("/"), sys.argv[2])
