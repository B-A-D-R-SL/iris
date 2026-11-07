# AI contribution: 50% or more AI-generated
"""NFR-04: paced real HTTP requests, isolated by pytest's live-server database."""

import json
import os
import subprocess
import sys
from http.client import HTTPConnection
from queue import Queue
from tempfile import TemporaryFile
from threading import Thread
from urllib.parse import urlsplit

import pytest
from django.conf import settings
from django.db import connection

from modules.accounts.tests.factories import UserFactory
from modules.households.tests.search_dataset import seed_search_dataset

pytestmark = pytest.mark.django_db(transaction=True)
REQUESTS_PER_SECOND = 100
REQUEST_COUNT = 300


@pytest.fixture
def search_server(transactional_db):
    # Functional API tests measure coverage; this process measures normal runtime
    # without coverage tracing or pytest's log-capture overhead.
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("COV_CORE_", "COVERAGE_"))
    }
    with TemporaryFile(mode="w+b") as errors:
        server = subprocess.Popen(
            [sys.executable, "-B", "-m", "modules.households.tests.search_load_server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
            env=env,
        )
        try:
            server.stdin.write(
                json.dumps(
                    {
                        "database": connection.settings_dict,
                        "secret_key": settings.SECRET_KEY,
                    }
                )
            )
            server.stdin.close()
            ready = Queue()
            Thread(
                target=lambda: ready.put(server.stdout.readline()), daemon=True
            ).start()
            line = ready.get(timeout=15)
            if not line:
                errors.seek(0)
                raise RuntimeError(errors.read().decode("utf-8"))
            yield json.loads(line)["url"]
        finally:
            server.terminate()
            server.wait(timeout=10)


def test_api_p95_under_500ms_at_100_requests_per_second(client, search_server):
    staff = UserFactory(role="intake_worker")
    seed_search_dataset(staff)
    client.force_login(staff)
    cookie = f"{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}"
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE households_household")
        cursor.execute("ANALYZE households_member")
    # A separate process keeps load generation/JSON parsing out of the server GIL.
    result = subprocess.run(
        [sys.executable, "-B", "-m", "modules.households.tests.search_load_client"],
        input=json.dumps(
            {
                "base": search_server,
                "cookie": cookie,
                "rps": REQUESTS_PER_SECOND,
                "count": REQUEST_COUNT,
            }
        ),
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    report = {"households": 5000, **json.loads(result.stdout)}
    print(json.dumps(report))
    assert report["requests"] == REQUEST_COUNT, report
    assert report["db_queries_max"] > 0, report
    assert report["cold_http_ms"] < 1000, report
    assert report["http_p95_ms"] < 500, report


def test_wsgi_reuses_database_connection_between_http_requests(client, search_server):
    """Catch per-request PostgreSQL reconnects without relying on wall-clock timing."""
    client.force_login(UserFactory(role="intake_worker"))
    cookie = f"{settings.SESSION_COOKIE_NAME}={client.cookies[settings.SESSION_COOKIE_NAME].value}"
    address = urlsplit(search_server)
    http = HTTPConnection(address.hostname, address.port, timeout=10)
    backend_pids = []
    try:
        for _ in range(2):
            http.request(
                "GET",
                "/api/staff/households/?q=missing-file",
                headers={"Cookie": cookie},
            )
            response = http.getresponse()
            response.read()
            assert response.status == 200
            backend_pids.append(response.getheader("X-Iris-Test-Db-Pid"))
    finally:
        http.close()
    assert backend_pids[0] is not None
    assert backend_pids[0] == backend_pids[1]
