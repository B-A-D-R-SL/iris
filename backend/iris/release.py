# AI contribution: 50% or more AI-generated
"""Supervise the web and queue processes together in the one-instance B1 plan."""

import logging
import os
import signal
import subprocess
import sys
from collections.abc import Sequence
from threading import Event

from iris.staging_views import WORKER_PID_FILE

logger = logging.getLogger("iris.deployment")


def _signal_group(pid: int, signum: signal.Signals) -> None:
    """A process may exit between poll and signal during a normal shutdown."""
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        logger.debug(
            "staging_process_already_exited",
            extra={"event": "staging_process_already_exited"},
        )


def _stop(children: Sequence[subprocess.Popen[bytes]]) -> None:
    """Forward shutdown to entire process groups, then enforce a bounded exit."""
    for child in children:
        if child.poll() is None:
            _signal_group(child.pid, signal.SIGTERM)
    for child in children:
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            _signal_group(child.pid, signal.SIGKILL)
            child.wait()


def _shutdown_event() -> Event:
    """Register PID 1 shutdown handling before setup or web processes start."""
    stopping = Event()

    def shutdown(signum: int, frame: object) -> None:
        stopping.set()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    return stopping


def _prepare(stopping: Event) -> int:
    """Forward cancellation to setup and wait for its database cleanup."""
    child = subprocess.Popen(
        [sys.executable, "-m", "iris.release", "--prepare"], start_new_session=True
    )
    try:
        while (result := child.poll()) is None:
            if stopping.wait(0.5):
                logger.info(
                    "staging_setup_cancelled",
                    extra={"event": "staging_setup_cancelled"},
                )
                return 0
        return result
    finally:
        if child.poll() is None:
            _stop([child])


def _serve(stopping: Event | None = None) -> int:
    """A dead worker makes the container fail rather than silently dropping jobs."""
    children: list[subprocess.Popen[bytes]] = []
    stopping = _shutdown_event() if stopping is None else stopping
    commands = [
        [sys.executable, "manage.py", "procrastinate", "worker", "--concurrency", "2"],
        [
            "gunicorn",
            "iris.wsgi:application",
            "--bind",
            "0.0.0.0:8000",
            "--workers",
            "2",
            "--timeout",
            "60",
            "--error-logfile",
            "-",
        ],
    ]
    try:
        for command in commands:
            if stopping.is_set():
                return 0
            children.append(subprocess.Popen(command, start_new_session=True))
        WORKER_PID_FILE.write_text(str(children[0].pid))
        while not stopping.is_set():
            if any(child.poll() is not None for child in children):
                logger.error(
                    "staging_process_exited", extra={"event": "staging_process_exited"}
                )
                return 1
            stopping.wait(0.5)
        return 0
    finally:
        WORKER_PID_FILE.unlink(missing_ok=True)
        _stop(children)


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iris.settings.staging")
    stopping = _shutdown_event()
    import django

    django.setup()
    WORKER_PID_FILE.unlink(missing_ok=True)
    if stopping.is_set():
        return 0
    result = _prepare(stopping)
    return result if result or stopping.is_set() else _serve(stopping)


def _run_setup() -> int:
    """Unwind migrations/seed and close DB sessions on setup cancellation."""

    def cancel(signum: int, frame: object) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    import django
    from django.core.management import call_command
    from django.db import connections

    try:
        django.setup()
        call_command("prepare_staging")
    finally:
        connections.close_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_setup() if sys.argv[1:] == ["--prepare"] else main())
