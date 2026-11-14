# AI contribution: 50% or more AI-generated
"""SET-17: the shared container shuts both processes down when either fails."""

import signal
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from iris import release


def test_dead_worker_fails_container_and_stops_web(tmp_path):
    worker, web = MagicMock(pid=101), MagicMock(pid=102)
    worker.poll.return_value = 1
    web.poll.return_value = None
    with (
        patch.object(release, "WORKER_PID_FILE", tmp_path / "worker.pid"),
        patch.object(release.signal, "signal"),
        patch.object(release.subprocess, "Popen", side_effect=[worker, web]),
        patch.object(release.os, "killpg") as kill,
    ):
        assert release._serve() == 1
    kill.assert_called_once_with(102, signal.SIGTERM)
    assert not (tmp_path / "worker.pid").exists()
    worker.wait.assert_called_once_with(timeout=30)


def test_signal_stops_both_process_groups(tmp_path):
    worker, web = MagicMock(pid=101), MagicMock(pid=102)
    worker.poll.return_value = web.poll.return_value = None
    event = MagicMock()
    event.is_set.side_effect = [False, True]
    with (
        patch.object(release, "WORKER_PID_FILE", tmp_path / "worker.pid"),
        patch.object(release, "Event", return_value=event),
        patch.object(release.signal, "signal") as signals,
        patch.object(release.subprocess, "Popen", side_effect=[worker, web]),
        patch.object(release.os, "killpg") as kill,
    ):
        assert release._serve() == 0
        signals.call_args_list[0].args[1](signal.SIGTERM, None)
    event.set.assert_called_once()
    assert [call.args for call in kill.call_args_list] == [
        (101, signal.SIGTERM),
        (102, signal.SIGTERM),
    ]


def test_hung_child_is_killed_after_shutdown_deadline():
    child = MagicMock(pid=101)
    child.poll.return_value = None
    child.wait.side_effect = [subprocess.TimeoutExpired("worker", 30), 0]
    with patch.object(release.os, "killpg") as kill:
        release._stop([child])
    assert [call.args for call in kill.call_args_list] == [
        (101, signal.SIGTERM),
        (101, signal.SIGKILL),
    ]


def test_already_exited_child_does_not_break_group_cleanup():
    with patch.object(release.os, "killpg", side_effect=ProcessLookupError) as kill:
        release._signal_group(101, signal.SIGTERM)
    kill.assert_called_once_with(101, signal.SIGTERM)


def test_web_spawn_failure_still_stops_worker(tmp_path):
    worker = MagicMock(pid=101)
    worker.poll.return_value = None
    with (
        patch.object(release, "WORKER_PID_FILE", tmp_path / "worker.pid"),
        patch.object(release.signal, "signal"),
        patch.object(
            release.subprocess,
            "Popen",
            side_effect=[worker, OSError("cannot start web")],
        ),
        patch.object(release.os, "killpg") as kill,
        pytest.raises(OSError, match="cannot start web"),
    ):
        release._serve()
    kill.assert_called_once_with(101, signal.SIGTERM)


@pytest.mark.parametrize("code", [0, 1])
def test_failed_setup_never_starts_web_or_worker(tmp_path, code):
    with (
        patch.object(release, "WORKER_PID_FILE", tmp_path / "worker.pid"),
        patch("django.setup"),
        patch.object(
            release.subprocess, "run", return_value=MagicMock(returncode=code)
        ),
        patch.object(release, "_serve", return_value=0) as serve,
    ):
        assert release.main() == code
    assert serve.call_count == (0 if code else 1)
