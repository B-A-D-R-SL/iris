# AI contribution: 50% or more AI-generated
"""Verify the new release, worker/DB readiness, SPA deep links and static assets."""

import json
import re
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def _get(url: str) -> bytes:
    headers = {"Cache-Control": "no-cache"}
    # Local release tests emulate App Service's trusted TLS terminator only on loopback.
    if url.startswith(("http://localhost:", "http://127.0.0.1:")):
        headers["X-Forwarded-Proto"] = "https"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=10) as response:
        return response.read()


def smoke(origin: str, revision: str, attempts: int = 90) -> None:
    """Old healthy replicas cannot satisfy a deployment of a different revision."""
    for attempt in range(attempts):
        try:
            payload = json.loads(_get(f"{origin}/api/ready/"))
            if payload != {"status": "ok", "revision": revision}:
                raise ValueError("New release is not ready.")
            html = _get(f"{origin}/sign-in").decode()
            asset = re.search(r'(?:src|href)="(/assets/[^"<>]+\.(?:js|css))"', html)
            if asset is None or not _get(f"{origin}{asset[1]}"):
                raise ValueError("Built frontend is unavailable.")
            if not _get(f"{origin}/static/admin/css/base.css"):
                raise ValueError("Collected admin assets are unavailable.")
            return
        except (URLError, OSError, ValueError):
            if attempt == attempts - 1:
                raise RuntimeError("Staging release smoke check failed.") from None
            time.sleep(5)


if __name__ == "__main__":
    smoke(sys.argv[1].rstrip("/"), sys.argv[2])
