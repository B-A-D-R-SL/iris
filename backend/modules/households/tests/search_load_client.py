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

    def get(self, term: str, scheduled: float) -> float:
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
        return perf_counter() - scheduled

    def close(self) -> None:
        for connection in self.connections:
            connection.close()


def run_load(base: str, cookie: str, rps: int, count: int) -> dict:
    client = LoadClient(base, cookie)
    pacing = Event()
    cold_started = perf_counter()
    client.get("IR-004234", cold_started)
    cold_ms = round((perf_counter() - cold_started) * 1000, 2)
    started = perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=16) as pool:
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
            durations = [future.result() for future in futures]
    finally:
        client.close()
    elapsed = perf_counter() - started
    return {
        "requests": len(durations),
        "cold_http_ms": cold_ms,
        "offered_rps": rps,
        "completed_rps": round(len(durations) / elapsed, 2),
        "http_p95_ms": round(quantiles(durations, n=100)[94] * 1000, 2),
        "http_max_ms": round(max(durations) * 1000, 2),
    }


if __name__ == "__main__":
    # The session cookie arrives through stdin and is never logged or stored.
    options = json.load(sys.stdin)
    print(json.dumps(run_load(**options)))
