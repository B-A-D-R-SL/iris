# AI contribution: 50% or more AI-generated
"""Tests for the ZAP gate (FIX-17). Run: python3 -m unittest discover -s .github/scripts"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

import zap_gate

RULES = """# comment line\t10049\tIGNORE
10020\tWARN\t(Anti-clickjacking Header) not accepted, only a warning
40012\tIGNORE\t(Cross Site Scripting) false positive on the docs page
"""


def report(*alerts: tuple[str, int]) -> dict:
    """A minimal ZAP JSON report with the given (plugin id, risk) alerts."""
    return {
        "site": [
            {
                "alerts": [
                    {
                        "pluginid": plugin,
                        "name": f"Alert {plugin}",
                        "riskcode": str(risk),
                        "instances": [{"uri": "http://localhost:8000/api/docs/"}],
                    }
                    for plugin, risk in alerts
                ]
            }
        ]
    }


class ZapGateTest(unittest.TestCase):
    def test_reads_only_ignored_plugins_and_skips_comments(self):
        self.assertEqual(zap_gate.ignored_plugins(RULES), {"40012"})

    def test_high_risk_alert_blocks(self):
        found = zap_gate.alerts(report(("40018", 3), ("10020", 2)))
        blocking = zap_gate.blocking(found, set())
        self.assertEqual([a.plugin_id for a in blocking], ["40018"])

    def test_accepted_high_risk_and_lower_risks_pass(self):
        found = zap_gate.alerts(report(("40012", 3), ("10020", 2), ("10049", 0)))
        self.assertEqual(zap_gate.blocking(found, {"40012"}), [])

    def test_main_returns_1_on_a_blocking_alert_and_0_otherwise(self):
        with tempfile.TemporaryDirectory() as folder:
            rules = Path(folder, "rules.tsv")
            rules.write_text(RULES, encoding="utf-8")
            bad = Path(folder, "bad.json")
            bad.write_text(json.dumps(report(("40018", 3))), encoding="utf-8")
            good = Path(folder, "good.json")
            good.write_text(json.dumps(report(("10020", 1))), encoding="utf-8")

            self.assertEqual(zap_gate.main(bad, rules), 1)
            self.assertEqual(zap_gate.main(good, rules), 0)

    def test_main_fails_when_the_report_is_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder, "zap-report.json")
            self.assertEqual(zap_gate.main(missing, Path(folder, "rules.tsv")), 2)

    def test_valid_scanned_site_with_zero_alerts_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "report.json")
            path.write_text(json.dumps(report()), encoding="utf-8")
            rules = Path(folder, "rules.tsv")
            rules.write_text("", encoding="utf-8")
            self.assertEqual(zap_gate.main(path, rules), 0)

    def test_malformed_scan_structure_never_passes_as_zero_alerts(self):
        malformed = [
            {},
            [],
            None,
            {"site": []},
            {"site": None},
            {"site": {}},
            {"site": [None]},
            {"site": [{}]},
            {"site": [{"alerts": None}]},
            {"site": [{"alerts": {}}]},
            {"site": [{"alerts": []}, {}]},
            {"site": [{"alerts": [None]}]},
            {"site": [{"alerts": [{}]}]},
            {"site": [{"alerts": [{"pluginid": "40018"}]}]},
            {"site": [{"alerts": [{"pluginid": "40018", "riskcode": True}]}]},
            {
                "site": [
                    {
                        "alerts": [
                            {"pluginid": "40018", "riskcode": "private-invalid-risk"}
                        ]
                    }
                ]
            },
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "report.json")
            rules = Path(folder, "rules.tsv")
            rules.write_text(RULES, encoding="utf-8")
            for data in malformed:
                with self.subTest(data=data), redirect_stderr(io.StringIO()) as errors:
                    path.write_text(json.dumps(data), encoding="utf-8")
                    self.assertEqual(zap_gate.main(path, rules), 2)
                    self.assertIn("::error::", errors.getvalue())
                    self.assertNotIn("private-invalid-risk", errors.getvalue())

    def test_invalid_json_and_encoding_fail_with_a_safe_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "report.json")
            rules = Path(folder, "rules.tsv")
            rules.write_text(RULES, encoding="utf-8")
            for payload in (b'{"site": private-invalid-json', b"\xff"):
                with (
                    self.subTest(payload=payload),
                    redirect_stderr(io.StringIO()) as errors,
                ):
                    path.write_bytes(payload)
                    self.assertEqual(zap_gate.main(path, rules), 2)
                    self.assertNotIn("private-invalid-json", errors.getvalue())

    def test_unreadable_report_or_rules_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "report.json")
            path.write_text(json.dumps(report()), encoding="utf-8")
            rules = Path(folder, "rules.tsv")
            for report_path, rules_path in (
                (Path(folder), rules),
                (path, rules),
            ):
                with self.subTest(report=report_path), redirect_stderr(io.StringIO()):
                    self.assertEqual(zap_gate.main(report_path, rules_path), 2)
            rules.write_bytes(b"\xff")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(zap_gate.main(path, rules), 2)

    def test_default_paths_are_inside_the_workspace(self):
        self.assertEqual(zap_gate.REPORT, Path("zap/zap-report.json"))
        self.assertEqual(zap_gate.RULES, Path(".zap/rules.tsv"))


if __name__ == "__main__":
    unittest.main()
