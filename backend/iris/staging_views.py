# AI contribution: 50% or more AI-generated
"""Serve the public SPA and identify a healthy staging release without secrets."""

import logging
import os
from pathlib import Path

from django.conf import settings
from django.db import DatabaseError, connection
from django.http import FileResponse, Http404, HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

logger = logging.getLogger("iris.deployment")
# Built as UID 10001's mode-0700 directory; other users cannot plant PID files.
WORKER_PID_FILE = Path("/run/iris/worker.pid")


@never_cache
@require_safe
def ready(request: HttpRequest) -> JsonResponse:
    """Check DB connectivity and the supervised worker process before smoke passes.

    Public by design: deployment probes call this without a session. Responses
    contain availability and the release revision only, never user data.
    """
    try:
        pid = int(WORKER_PID_FILE.read_text())
        if pid <= 1:
            raise ValueError
        os.kill(pid, 0)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except (DatabaseError, OSError, ValueError):
        logger.error("staging_not_ready", extra={"event": "staging_not_ready"})
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse(
        {"status": "ok", "revision": os.environ.get("IRIS_RELEASE_SHA", "local")}
    )


@never_cache
@require_safe
def spa(request: HttpRequest, path: str = "") -> FileResponse:
    """Allow React deep links, while missing assets and backend URLs stay 404."""
    index = settings.BASE_DIR / "frontend_dist" / "index.html"
    if "." in path.rsplit("/", 1)[-1] or not index.is_file():
        raise Http404
    return FileResponse(index.open("rb"), content_type="text/html")
