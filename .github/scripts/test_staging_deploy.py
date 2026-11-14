# AI contribution: 50% or more AI-generated
"""SET-17 deployment trust boundaries and failed smoke checks."""

import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

import staging_gate
import staging_smoke

SHA = "a" * 40
REPOSITORY = {"full_name": "B-A-D-R-SL/iris"}


def event():
    return {
        "repository": REPOSITORY,
        "workflow_run": {
            "event": "push",
            "head_branch": "main",
            "head_sha": SHA,
            "head_repository": REPOSITORY,
            "conclusion": "success",
        },
    }


def api_results(conclusion="success", head=SHA):
    return [
        {"object": {"sha": head}},
        {"workflow_runs": [{"head_sha": SHA, "conclusion": conclusion}]},
    ]


class DeploymentGateTest(unittest.TestCase):
    def test_success_uses_ci_revision_not_workflow_default_sha(self):
        with patch.object(staging_gate, "_api", side_effect=api_results()):
            result = staging_gate.verified_sha(
                event(), "workflow_run", "b" * 40, "refs/heads/main"
            )
        self.assertEqual(result, SHA)

    def test_refuses_pr_fork_failed_and_nonmain_runs(self):
        cases = [
            ("event", "pull_request"),
            ("head_branch", "feature"),
            ("conclusion", "failure"),
            ("head_repository", {"full_name": "fork/iris"}),
            ("head_sha", "bad revision"),
        ]
        for field, value in cases:
            with self.subTest(field=field), patch.object(staging_gate, "_api") as api:
                payload = event()
                payload["workflow_run"][field] = value
                with self.assertRaises(ValueError):
                    staging_gate.verified_sha(
                        payload, "workflow_run", SHA, "refs/heads/main"
                    )
                api.assert_not_called()

    def test_refuses_stale_or_currently_failed_ci(self):
        for responses in [
            api_results(head="b" * 40),
            api_results("failure"),
            api_results(None),
            [{"object": {"sha": SHA}}, {"workflow_runs": []}],
        ]:
            with (
                self.subTest(responses=responses),
                patch.object(staging_gate, "_api", side_effect=responses),
                self.assertRaises(ValueError),
            ):
                staging_gate.verified_sha(
                    event(), "workflow_run", SHA, "refs/heads/main"
                )

    def test_manual_retry_requires_main_and_successful_ci(self):
        with patch.object(staging_gate, "_api", side_effect=api_results()):
            self.assertEqual(
                staging_gate.verified_sha(
                    event(), "workflow_dispatch", SHA, "refs/heads/main"
                ),
                SHA,
            )
        with self.assertRaises(ValueError):
            staging_gate.verified_sha(
                event(), "workflow_dispatch", SHA, "refs/heads/feature"
            )

    def test_foreign_repository_never_queries_or_deploys(self):
        with self.assertRaises(ValueError):
            staging_gate.verified_sha(
                {"repository": {"full_name": "other/iris"}},
                "workflow_dispatch",
                SHA,
                "refs/heads/main",
            )


class DeploymentSmokeTest(unittest.TestCase):
    def test_checks_revision_deep_link_and_both_asset_trees(self):
        responses = [
            json.dumps({"status": "ok", "revision": SHA}).encode(),
            b'<script src="/assets/index-abc.js"></script>',
            b"javascript",
            b"admin css",
        ]
        with patch.object(staging_smoke, "_get", side_effect=responses) as get:
            staging_smoke.smoke("https://iris.example", SHA, attempts=1)
        self.assertEqual(
            [call.args[0] for call in get.call_args_list],
            [
                "https://iris.example/api/ready/",
                "https://iris.example/sign-in",
                "https://iris.example/assets/index-abc.js",
                "https://iris.example/static/admin/css/base.css",
            ],
        )

    def test_old_replica_missing_assets_and_connection_errors_fail(self):
        cases = [
            [json.dumps({"status": "ok", "revision": "b" * 40}).encode()],
            [json.dumps({"status": "ok", "revision": SHA}).encode(), b"no assets"],
            [URLError("unavailable")],
        ]
        for responses in cases:
            with (
                self.subTest(responses=responses),
                patch.object(staging_smoke, "_get", side_effect=responses),
                self.assertRaisesRegex(RuntimeError, "smoke check failed"),
            ):
                staging_smoke.smoke("https://iris.example", SHA, attempts=1)

    def test_waits_for_new_revision_with_bounded_retries(self):
        responses = [
            URLError("starting"),
            json.dumps({"status": "ok", "revision": SHA}).encode(),
            b'<script src="/assets/index-abc.js"></script>',
            b"js",
            b"css",
        ]
        with (
            patch.object(staging_smoke, "_get", side_effect=responses),
            patch.object(staging_smoke.time, "sleep") as sleep,
        ):
            staging_smoke.smoke("https://iris.example", SHA, attempts=2)
        sleep.assert_called_once_with(5)

    def test_requests_every_script_and_stylesheet_in_either_order(self):
        for assets in [("bundle.js", "styles.css"), ("styles.css", "bundle.js")]:
            html = f'<script src="/assets/{assets[0]}"></script><link href="/assets/{assets[1]}">'.encode()
            responses = [
                json.dumps({"status": "ok", "revision": SHA}).encode(),
                html,
                b"first",
                b"second",
                b"admin",
            ]
            with (
                self.subTest(assets=assets),
                patch.object(staging_smoke, "_get", side_effect=responses) as get,
            ):
                staging_smoke.smoke("https://iris.example", SHA, attempts=1)
            self.assertEqual(
                [c.args[0] for c in get.call_args_list][2:4],
                [f"https://iris.example/assets/{a}" for a in assets],
            )

    def test_broken_second_asset_fails_for_both_asset_orders(self):
        for first, second in [("bundle.js", "styles.css"), ("styles.css", "bundle.js")]:
            html = f'<script src="/assets/{first}"></script><link href="/assets/{second}">'.encode()
            responses = [
                json.dumps({"status": "ok", "revision": SHA}).encode(),
                html,
                b"working",
                URLError("second asset missing"),
            ]
            with (
                self.subTest(first=first),
                patch.object(staging_smoke, "_get", side_effect=responses),
                self.assertRaisesRegex(RuntimeError, "smoke check failed"),
            ):
                staging_smoke.smoke("https://iris.example", SHA, attempts=1)


if __name__ == "__main__":
    unittest.main()
