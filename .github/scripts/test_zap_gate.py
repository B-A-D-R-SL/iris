# AI contribution: 50% or more AI-generated
"""Tests for the ZAP gate (FIX-17). Run: python3 -m unittest discover -s .github/scripts"""

import json
import tempfile
import unittest
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

            self.assertEqual(zap_gate.main(["zap_gate.py", str(bad), str(rules)]), 1)
            self.assertEqual(zap_gate.main(["zap_gate.py", str(good), str(rules)]), 0)

    def test_main_needs_two_arguments(self):
        self.assertEqual(zap_gate.main(["zap_gate.py"]), 2)


if __name__ == "__main__":
    unittest.main()
