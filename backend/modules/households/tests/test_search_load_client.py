# AI contribution: 50% or more AI-generated
"""The HTTP load driver must measure queues and support concurrent requests."""

from threading import Event, Lock

import pytest

from modules.households.tests import search_load_client as driver


def test_latency_separates_client_queue_from_request_time(monkeypatch):
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
    ready = Event()
    lock = Lock()
    calls = 0

    class Client:
        def __init__(self, *args):
            pass

        def get(self, term, scheduled):
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
