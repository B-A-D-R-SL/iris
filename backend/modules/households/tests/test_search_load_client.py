# AI contribution: 50% or more AI-generated
"""The HTTP load driver must measure queues and support concurrent requests."""

import subprocess
import sys
from threading import Event, Lock

import pytest

from modules.households.tests import search_load_client as driver


def test_benchmark_children_do_not_inherit_coverage_instrumentation(monkeypatch):
    """Both child processes must retain app settings without tracing hooks."""
    monkeypatch.setenv("COVERAGE_PROCESS_CONFIG", "test-configuration")
    monkeypatch.setenv("COVERAGE_FILE", "/tmp/unused-test-coverage")
    monkeypatch.setenv("COV_CORE_SOURCE", "test-source")
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "iris.settings.test")

    environment = driver.uninstrumented_environment()

    assert environment["DJANGO_SETTINGS_MODULE"] == "iris.settings.test"
    assert "COVERAGE_PROCESS_CONFIG" not in environment
    assert "COVERAGE_FILE" not in environment
    assert "COV_CORE_SOURCE" not in environment
    assert driver.os.environ["COVERAGE_PROCESS_CONFIG"] == "test-configuration"


def test_benchmark_child_starts_without_active_coverage():
    """Exercise real coverage startup hooks when this test runs under coverage."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import coverage; print(coverage.Coverage.current() is None)",
        ],
        env=driver.uninstrumented_environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    assert result.stdout.strip() == "True"


@pytest.mark.parametrize(
    ("status", "payload", "error"),
    [
        (403, b"<html>Forbidden</html>", "Search load request failed: HTTP 403"),
        (500, b"<html>Unavailable</html>", "Search load request failed: HTTP 500"),
        (200, b"not JSON", "Invalid household search response"),
        (200, b"\xff", "Invalid household search response"),
        (200, b"[]", "Invalid household search response"),
        (200, b"null", "Invalid household search response"),
        (200, b"42", "Invalid household search response"),
        (200, b"{}", "Invalid household search response"),
        (200, b'{"results": null}', "Invalid household search response"),
        (200, b'{"results": {}}', "Invalid household search response"),
    ],
)
def test_load_rejects_http_errors_and_malformed_responses(
    monkeypatch, status, payload, error
):
    """Preserve HTTP failures even when the server sends HTML or invalid JSON."""

    class Response:
        def read(self):
            return payload

    response = Response()
    response.status = status

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return response

        def close(self):
            pass

    monkeypatch.setattr(driver, "HTTPConnection", Connection)
    client = driver.LoadClient("http://localhost:8000", "test-cookie")
    try:
        with pytest.raises(RuntimeError, match=error):
            client.get("private-search", scheduled=0)
    finally:
        client.close()


def test_latency_separates_client_queue_from_request_time(monkeypatch):
    """Distinguish client queue delay from the time spent executing a request."""

    class Response:
        status = 200

        def read(self):
            return b'{"results": []}'

        def getheader(self, name):
            return {
                "X-Iris-Test-App-Ms": "250",
                "X-Iris-Test-Db-Ms": "100",
                "X-Iris-Test-Db-Queries": "6",
            }[name]

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    clock = iter((10.2, 10.5))
    monkeypatch.setattr(driver, "perf_counter", lambda: next(clock))
    monkeypatch.setattr(driver, "HTTPConnection", Connection)
    client = driver.LoadClient("http://localhost:8000", "test-cookie")
    try:
        sample = client.get("test", scheduled=10)
    finally:
        client.close()
    assert sample == pytest.approx(
        {
            "http_ms": 500,
            "queue_ms": 200,
            "request_ms": 300,
            "app_ms": 250,
            "db_ms": 100,
            "db_queries": 6,
        }
    )


def test_load_can_offer_requests_while_32_are_in_flight(monkeypatch):
    """Detect a client worker limit that queues otherwise permissible requests."""
    ready = Event()
    lock = Lock()
    calls = 0

    class Client:
        def __init__(self, *args):
            pass

        def get(self, term, scheduled):
            """Hold requests until the driver has exercised its concurrency budget."""
            nonlocal calls
            with lock:
                calls += 1
                current = calls
                if current == 33:  # Cold request plus 32 concurrent requests.
                    ready.set()
            if current > 1 and not ready.wait(timeout=5):
                raise RuntimeError("The load client stalled before 32 requests.")
            return dict.fromkeys(
                ("http_ms", "queue_ms", "request_ms", "app_ms", "db_ms", "db_queries"),
                0.0,
            )

        def close(self):
            pass

    monkeypatch.setattr(driver, "LoadClient", Client)
    report = driver.run_load("http://localhost", "test-cookie", rps=100, count=40)
    assert ready.is_set()
    assert report["requests"] == 40
    assert calls == 41


def test_cold_request_failure_closes_client_connections(monkeypatch):
    """Release client resources even when the first HTTP request is refused."""
    closed = Event()

    class Client:
        def __init__(self, *args):
            pass

        def get(self, *args):
            raise RuntimeError("Search load request failed: HTTP 403")

        def close(self):
            closed.set()

    monkeypatch.setattr(driver, "LoadClient", Client)
    with pytest.raises(RuntimeError, match="HTTP 403"):
        driver.run_load("http://localhost", "test-cookie", rps=100, count=40)
    assert closed.is_set()
