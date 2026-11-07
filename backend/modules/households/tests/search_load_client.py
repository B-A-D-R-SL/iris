# AI contribution: 50% or more AI-generated
"""Separate-process HTTP driver: keep client work outside the server's Python GIL."""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from statistics import quantiles
from threading import Event, Lock, local
from time import perf_counter
from urllib.parse import urlencode, urlsplit

SEARCH_TERMS = (
    "Élod",
    "foyer-04234@example.test",
    "IR-004234",
    "rue emile",
    "missing-file",
)
# At 100 requests/second and 500 ms, 50 requests may legitimately be in flight.
# Leave headroom so the client does not impose a tighter concurrency limit.
CLIENT_WORKERS = 64


class LoadClient:
    def __init__(self, base: str, cookie: str):
        address = urlsplit(base)
        if address.hostname is None:
            raise ValueError("The load server must have a hostname.")
        self.host = address.hostname
        self.port = address.port
        self.cookie = cookie
        self.worker = local()
        self.connections: list[HTTPConnection] = []
        self.lock = Lock()

    def get(self, term: str, scheduled: float) -> dict[str, float]:
        started = perf_counter()
        if not hasattr(self.worker, "connection"):
            self.worker.connection = HTTPConnection(self.host, self.port, timeout=10)
            with self.lock:
                self.connections.append(self.worker.connection)
        connection = self.worker.connection
        connection.request(
            "GET",
            "/api/staff/households/?" + urlencode({"q": term}),
            headers={"Cookie": self.cookie, "Accept": "application/json"},
        )
        response = connection.getresponse()
        body = json.loads(response.read())
        if response.status != 200 or "results" not in body:
            raise RuntimeError(f"Search load request failed: HTTP {response.status}")
        finished = perf_counter()
        return {
            "http_ms": (finished - scheduled) * 1000,
            "queue_ms": (started - scheduled) * 1000,
            "request_ms": (finished - started) * 1000,
            "app_ms": float(response.getheader("X-Iris-Test-App-Ms") or 0),
            "db_ms": float(response.getheader("X-Iris-Test-Db-Ms") or 0),
            "db_queries": float(response.getheader("X-Iris-Test-Db-Queries") or 0),
        }

    def close(self) -> None:
        for connection in self.connections:
            connection.close()


def run_load(base: str, cookie: str, rps: int, count: int) -> dict:
    client = LoadClient(base, cookie)
    pacing = Event()
    try:
        cold_ms = client.get("IR-004234", perf_counter())["http_ms"]
        started = perf_counter()
        with ThreadPoolExecutor(max_workers=CLIENT_WORKERS) as pool:
            futures = []
            for index in range(count):
                scheduled = started + index / rps
                # Explicit request pacing, not synchronization by arbitrary sleeps.
                pacing.wait(max(0, scheduled - perf_counter()))
                futures.append(
                    pool.submit(
                        client.get, SEARCH_TERMS[index % len(SEARCH_TERMS)], scheduled
                    )
                )
            samples = [future.result() for future in futures]
    finally:
        client.close()
    elapsed = perf_counter() - started
    return _report(samples, cold_ms, elapsed, rps)


def _report(samples: list[dict[str, float]], cold_ms: float, elapsed: float, rps: int):
    def p95(key: str) -> float:
        return round(quantiles([sample[key] for sample in samples], n=100)[94], 2)

    return {
        "requests": len(samples),
        "cold_http_ms": round(cold_ms, 2),
        "offered_rps": rps,
        "completed_rps": round(len(samples) / elapsed, 2),
        "client_workers": CLIENT_WORKERS,
        "http_p95_ms": p95("http_ms"),
        "http_max_ms": round(max(sample["http_ms"] for sample in samples), 2),
        "client_queue_p95_ms": p95("queue_ms"),
        "request_p95_ms": p95("request_ms"),
        "app_p95_ms": p95("app_ms"),
        "db_p95_ms": p95("db_ms"),
        "db_queries_max": int(max(sample["db_queries"] for sample in samples)),
    }


if __name__ == "__main__":
    # The session cookie arrives through stdin and is never logged or stored.
    options = json.load(sys.stdin)
    print(json.dumps(run_load(**options)))
