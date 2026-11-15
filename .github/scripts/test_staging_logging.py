# AI contribution: 50% or more AI-generated
"""Keep deployment failures observable without disclosing exception contents."""

import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

import staging_gate
import staging_smoke
from test_staging_smoke_deadline import Clock

SHA = "a" * 40
PRIVATE = "https://private.example/?token=must-not-appear"


class StagingLoggingTest(unittest.TestCase):
    def test_deadline_expiry_after_retry_sleep_is_logged(self):
        clock = Clock()
        with (
            patch.object(
                staging_smoke, "_verify_release", side_effect=URLError(PRIVATE)
            ),
            patch.object(staging_smoke.time, "monotonic", clock.monotonic),
            patch.object(staging_smoke.time, "sleep", clock.sleep),
            self.assertLogs("staging_smoke", level="WARNING") as captured,
            self.assertRaises(RuntimeError),
        ):
            staging_smoke.smoke("https://iris.example", SHA, timeout=1)
        self.assertEqual(clock.elapsed, 1)
        self.assertEqual(len(captured.records), 2)
        self.assertEqual(captured.records[-1].levelname, "ERROR")
        self.assertEqual(captured.records[-1].event, "staging_smoke_failed")
        self.assertEqual(captured.records[-1].error_type, "TimeoutError")
        self.assertNotIn(PRIVATE, "\n".join(captured.output))

    def test_smoke_logs_a_failed_attempt_before_a_successful_retry(self):
        with (
            patch.object(
                staging_smoke, "_verify_release", side_effect=[URLError(PRIVATE), None]
            ),
            patch.object(staging_smoke.time, "sleep"),
            self.assertLogs("staging_smoke", level="WARNING") as captured,
        ):
            staging_smoke.smoke("https://iris.example", SHA, attempts=2)
        self.assertEqual(len(captured.records), 1)
        record = captured.records[0]
        self.assertEqual(record.event, "staging_smoke_attempt_failed")
        self.assertEqual(record.attempt, 1)
        self.assertEqual(record.error_type, "URLError")
        self.assertIn("1", record.getMessage())
        self.assertIn("URLError", record.getMessage())
        self.assertNotIn(PRIVATE, "\n".join(captured.output))

    def test_terminal_smoke_failure_logs_type_without_private_exception(self):
        with (
            patch.object(
                staging_smoke, "_verify_release", side_effect=ValueError(PRIVATE)
            ),
            self.assertLogs("staging_smoke", level="WARNING") as captured,
            self.assertRaisesRegex(
                RuntimeError, "^Staging release smoke check failed.$"
            ),
        ):
            staging_smoke.smoke("https://iris.example", SHA, attempts=1)
        self.assertEqual(captured.records[0].event, "staging_smoke_attempt_failed")
        self.assertEqual(captured.records[0].error_type, "ValueError")
        self.assertEqual(captured.records[0].attempt, 1)
        self.assertNotIn(PRIVATE, "\n".join(captured.output))

    def test_gate_logs_each_refusal_type_with_github_annotation_and_no_secrets(self):
        environment = {
            "GITHUB_EVENT_PATH": "unused-event.json",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_SHA": SHA,
            "GITHUB_REF": "refs/heads/main",
        }
        for error in [
            ValueError(PRIVATE),
            KeyError(PRIVATE),
            OSError(PRIVATE),
            URLError(PRIVATE),
        ]:
            with (
                self.subTest(error=type(error).__name__),
                patch.dict(staging_gate.os.environ, environment, clear=True),
                patch.object(
                    staging_gate.Path, "read_text", return_value=json.dumps({})
                ),
                patch.object(staging_gate, "verified_sha", side_effect=error),
                self.assertLogs("staging_gate", level="ERROR") as captured,
            ):
                self.assertEqual(staging_gate.main(), 1)
            self.assertEqual(len(captured.records), 1)
            record = captured.records[0]
            self.assertEqual(record.event, "staging_deployment_refused")
            self.assertEqual(record.error_type, type(error).__name__)
            self.assertTrue(record.getMessage().startswith("::error::"))
            self.assertIn(type(error).__name__, record.getMessage())
            self.assertNotIn(PRIVATE, "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
