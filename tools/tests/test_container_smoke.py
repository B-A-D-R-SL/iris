# AI contribution: 50% or more AI-generated
"""Offline checks for the smoke runner's restricted local HTTP boundary."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BASH = shutil.which("bash")
SCRIPT = Path(__file__).resolve().parents[1] / "container-smoke.sh"
FAKES = """
source "$1"
compose() {
  printf '%s' "$COMPOSE_OUTPUT"
  return "${COMPOSE_STATUS:-0}"
}
curl() {
  printf '%s\\0' "$@" > "$CURL_ARGS"
  printf '%s' "$CURL_OUTPUT"
  return "${CURL_STATUS:-0}"
}
"""


class HttpBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if BASH is None:
            raise RuntimeError("Bash is required for the container smoke runner")

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="iris-smoke-boundary-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.arguments = self.root / "curl-arguments"

    def run_bash(self, body, *, fakes=True, strict=True, **variables):
        self.arguments.unlink(missing_ok=True)
        environment = os.environ.copy()
        environment.pop("BASH_ENV", None)
        environment.update(
            COMPOSE_OUTPUT="127.0.0.1:5173\n",
            COMPOSE_STATUS="0",
            CURL_ARGS=str(self.arguments),
            CURL_OUTPUT='{"status": "ok"}',
            CURL_STATUS="0",
        )
        environment.update(variables)
        command = (
            ("set -euo pipefail\n" if strict else "") + (FAKES if fakes else "") + body
        )
        return subprocess.run(
            [
                BASH,
                "--noprofile",
                "--norc",
                "-c",
                command,
                "smoke-boundary",
                str(SCRIPT),
            ],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def assert_curl_arguments(self, port, path):
        arguments = self.arguments.read_bytes().decode().split("\0")[:-1]
        self.assertEqual(
            arguments,
            [
                "--disable",
                "--noproxy",
                "*",
                "--proto",
                "=http",
                "--fail",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "1",
                "--max-time",
                "10",
                f"http://127.0.0.1:{port}{path}",
            ],
        )

    def test_sourcing_has_no_startup_effects(self):
        result = self.run_bash(
            """
IRIS_UID=unchanged
flags_before=$-
options_before=$(set -o)
git() { return 99; }
docker() { return 99; }
source "$1"
[[ "$IRIS_UID" == unchanged && "$-" == "$flags_before" ]] || exit 1
[[ "$(set -o)" == "$options_before" ]] || exit 1
[[ -z "${repo_dir+x}" && -z "${smoke_dir+x}" ]] || exit 1
[[ -z "$(trap -p EXIT INT TERM)" ]] || exit 1
declare -F frontend_get > /dev/null
""",
            fakes=False,
            strict=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_allowed_paths_and_decimal_port_boundaries(self):
        for port, normalized in [("1", "1"), ("65535", "65535"), ("00009", "9")]:
            for path in ["/", "/api/health/", "/src/main.tsx"]:
                with self.subTest(port=port, path=path):
                    result = self.run_bash(
                        'set_frontend_port; frontend_get "$PROBE_PATH"',
                        COMPOSE_OUTPUT=f"127.0.0.1:{port}\n",
                        PROBE_PATH=path,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assert_curl_arguments(normalized, path)

    def test_rejects_untrusted_addresses_and_invalid_ports_without_curl(self):
        addresses = [
            "0.0.0.0:5173",
            "localhost:5173",
            "[::1]:5173",
            "127.0.0.2:5173",
            "192.0.2.1:5173",
            "",
            "127.0.0.1:0",
            "127.0.0.1:65536",
            "127.0.0.1:100000",
            "127.0.0.1:-1",
            "127.0.0.1:+1",
            "127.0.0.1:1/path",
            " 127.0.0.1:5173",
            "127.0.0.1:5173\n192.0.2.1:5173",
            "127.0.0.1:$(exit 99)",
        ]
        for address in addresses:
            with self.subTest(address=address):
                result = self.run_bash(
                    "set_frontend_port; frontend_get /",
                    COMPOSE_OUTPUT=address,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.arguments.exists())

    def test_failed_port_lookup_propagates_status_without_curl(self):
        result = self.run_bash(
            "set_frontend_port; frontend_get /",
            COMPOSE_STATUS="23",
        )
        self.assertEqual(result.returncode, 23)
        self.assertFalse(self.arguments.exists())

    def test_invalid_replacement_clears_previously_valid_port(self):
        result = self.run_bash(
            """
frontend_port=5173
if set_frontend_port; then exit 99; fi
[[ -z "$frontend_port" ]]
frontend_get /
""",
            COMPOSE_OUTPUT="0.0.0.0:5173",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.arguments.exists())

    def test_unvalidated_port_cannot_be_probed(self):
        result = self.run_bash("frontend_get /")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.arguments.exists())

    def test_rejects_unexpected_paths_without_curl(self):
        for path in [
            "",
            "//untrusted.invalid/",
            "/../",
            "/api/health/?next=other",
            "/api/health/#other",
            "https://untrusted.invalid/",
            "-K",
            "/src/main.tsx\n/other",
        ]:
            with self.subTest(path=path):
                result = self.run_bash(
                    'set_frontend_port; frontend_get "$PROBE_PATH"',
                    PROBE_PATH=path,
                )
                self.assertEqual(result.returncode, 1)
                self.assertFalse(self.arguments.exists())

        for invocation in ["frontend_get", "frontend_get / /other"]:
            with self.subTest(invocation=invocation):
                result = self.run_bash(f"set_frontend_port; {invocation}")
                self.assertEqual(result.returncode, 1)
                self.assertFalse(self.arguments.exists())

    def test_curl_errors_and_unhealthy_responses_are_failures(self):
        result = self.run_bash("set_frontend_port; frontend_get /", CURL_STATUS="22")
        self.assertEqual(result.returncode, 22)
        result = self.run_bash("set_frontend_port; health_ready", CURL_STATUS="7")
        self.assertEqual(result.returncode, 7)
        result = self.run_bash(
            "set_frontend_port; health_ready", CURL_OUTPUT="unhealthy"
        )
        self.assertEqual(result.returncode, 1)

    def test_proxy_and_curl_config_cannot_change_probe_options(self):
        (self.root / ".curlrc").write_text(
            'location\nproxy = "proxy.invalid:8080"\nurl = "https://untrusted.invalid/"\n',
        )
        result = self.run_bash(
            "set_frontend_port; health_ready",
            CURL_HOME=str(self.root),
            http_proxy="proxy.invalid:8080",
            HTTPS_PROXY="proxy.invalid:8080",
            ALL_PROXY="proxy.invalid:8080",
            NO_PROXY="",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_curl_arguments("5173", "/api/health/")


if __name__ == "__main__":
    unittest.main()
