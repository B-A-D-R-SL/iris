# AI contribution: 50% or more AI-generated
"""Exercise the staging startup allowance without real waits or network calls."""

import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

import staging_smoke

SHA = "a" * 40


class Clock:
    def __init__(self):
        self.elapsed = 0.0

    def monotonic(self):
        return self.elapsed

    def sleep(self, duration):
        self.elapsed += duration


class StartupDeadlineTest(unittest.TestCase):
    def test_release_starting_after_old_retry_window_can_still_pass(self):
        clock = Clock()
        responses = {
            "/api/ready/": json.dumps({"status": "ok", "revision": SHA}).encode(),
            "/sign-in": b'<script src="/assets/app.js"></script>',
            "/assets/app.js": b"javascript",
            "/static/admin/css/base.css": b"stylesheet",
        }

        def get(url, **kwargs):
            if clock.elapsed < 590:
                raise URLError("Still starting")
            return responses[url.removeprefix("https://iris.example")]

        with (
            patch.object(staging_smoke, "_get", side_effect=get),
            patch.object(staging_smoke.time, "monotonic", clock.monotonic),
            patch.object(staging_smoke.time, "sleep", clock.sleep),
        ):
            try:
                staging_smoke.smoke("https://iris.example", SHA)
            except RuntimeError:
                self.fail("A release ready within the 600-second allowance was refused")
        self.assertEqual(clock.elapsed, 590)

    def test_unavailable_release_uses_full_startup_allowance_then_fails(self):
        clock = Clock()
        with (
            patch.object(staging_smoke, "_get", side_effect=URLError("Starting")),
            patch.object(staging_smoke.time, "monotonic", clock.monotonic),
            patch.object(staging_smoke.time, "sleep", clock.sleep),
            self.assertRaisesRegex(RuntimeError, "smoke check failed"),
        ):
            staging_smoke.smoke("https://iris.example", SHA)
        self.assertEqual(clock.elapsed, 600)

    def test_last_retry_sleep_stops_at_the_deadline(self):
        clock = Clock()
        with (
            patch.object(staging_smoke, "_get", side_effect=URLError("Starting")),
            patch.object(staging_smoke.time, "monotonic", clock.monotonic),
            patch.object(staging_smoke.time, "sleep", clock.sleep),
            self.assertRaises(RuntimeError),
        ):
            staging_smoke.smoke("https://iris.example", SHA, timeout=7)
        self.assertEqual(clock.elapsed, 7)

    def test_request_timeout_uses_only_the_remaining_startup_allowance(self):
        with (
            patch.object(staging_smoke.time, "monotonic", return_value=598),
            patch.object(staging_smoke, "urlopen") as request,
        ):
            staging_smoke._get("https://iris.example/api/ready/", deadline=600)
        self.assertEqual(request.call_args.kwargs["timeout"], 2)

    def test_expired_deadline_makes_no_network_request(self):
        with (
            patch.object(staging_smoke.time, "monotonic", return_value=600),
            patch.object(staging_smoke, "urlopen") as request,
            self.assertRaises(TimeoutError),
        ):
            staging_smoke._get("https://iris.example/api/ready/", deadline=600)
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
