# AI contribution: 50% or more AI-generated
"""Uninstrumented loopback WSGI server restricted to pytest's temporary database."""

import json
import os
import sys
from time import perf_counter

import django
from django.conf import settings
from django.core.servers.basehttp import ThreadedWSGIServer
from django.db import connection
from django.test.testcases import QuietWSGIRequestHandler


def _timed_application(application):
    """Expose aggregate timings only on the isolated test server, without SQL/PII."""

    def timed(environ, start_response):
        """Measure the request and its queries without logging SQL or parameters."""
        started = perf_counter()
        database_seconds = 0.0
        queries = 0

        def execute(executor, sql, params, many, context):
            nonlocal database_seconds, queries
            query_started = perf_counter()
            queries += 1
            try:
                return executor(sql, params, many, context)
            finally:
                database_seconds += perf_counter() - query_started

        def response(status, headers, exc_info=None):
            """Expose numeric test diagnostics alongside the application's response."""
            headers = [
                *headers,
                ("X-Iris-Test-App-Ms", str((perf_counter() - started) * 1000)),
                ("X-Iris-Test-Db-Ms", str(database_seconds * 1000)),
                ("X-Iris-Test-Db-Queries", str(queries)),
            ]
            if connection.connection is not None:
                headers.append(
                    ("X-Iris-Test-Db-Pid", str(connection.connection.info.backend_pid))
                )
            return start_response(status, headers, exc_info)

        with connection.execute_wrapper(execute):
            return application(environ, response)

    return timed


def serve() -> None:
    """Start an uninstrumented loopback server restricted to a disposable database."""
    options = json.load(sys.stdin)
    database = options["database"]
    if not database["NAME"].startswith("test_"):
        raise ValueError("Load tests must use a disposable test_ database.")
    os.environ["DJANGO_SETTINGS_MODULE"] = "iris.settings.test"
    settings.DATABASES = {"default": database}
    settings.SECRET_KEY = options["secret_key"]
    settings.ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
    django.setup()
    # Use the application's real startup/readiness path. No HTTP request or
    # household search runs before the client measures its first request.
    from iris.wsgi import application

    server = ThreadedWSGIServer(("127.0.0.1", 0), QuietWSGIRequestHandler)
    server.set_app(_timed_application(application))
    print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}"}), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
