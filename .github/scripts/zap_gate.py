# AI contribution: 50% or more AI-generated
"""ZAP baseline gate (FIX-17, SEC-10): fail on High-risk alerts.

Run from the repository root by the zap-baseline job in .github/workflows/ci.yml:

    python3 .github/scripts/zap_gate.py

It reads the fixed paths zap/zap-report.json and .zap/rules.tsv; it takes no
path arguments, so nothing outside the workspace can be read through it.

ZAP's own exit code also counts Low and Medium warnings, so the job ignores it
and this script decides: any High-risk alert whose plugin is not set to IGNORE
in rules.tsv fails the job. Lower risks are listed but do not fail it.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Fixed paths, relative to the repository root where the CI step runs.
REPORT = Path("zap/zap-report.json")
RULES = Path(".zap/rules.tsv")

HIGH = 3
RISK_NAMES = {0: "Informational", 1: "Low", 2: "Medium", 3: "High"}


@dataclass(frozen=True)
class Alert:
    plugin_id: str
    name: str
    risk: int
    instances: int


def ignored_plugins(rules_text: str) -> set[str]:
    """Plugin IDs set to IGNORE in rules.tsv; comment lines start with #."""
    ignored = set()
    for line in rules_text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].strip() == "IGNORE":
            ignored.add(parts[0].strip())
    return ignored


def alerts(report: dict) -> list[Alert]:
    """Every alert in a ZAP JSON report (-J), across all scanned sites."""
    found = []
    for site in report.get("site", []):
        for alert in site.get("alerts", []):
            found.append(
                Alert(
                    plugin_id=str(alert.get("pluginid", "")),
                    name=str(alert.get("name") or alert.get("alert", "")),
                    risk=int(alert.get("riskcode", 0)),
                    instances=len(alert.get("instances", [])),
                )
            )
    return found


def blocking(found: list[Alert], ignored: set[str]) -> list[Alert]:
    """High-risk alerts that rules.tsv does not accept."""
    return [a for a in found if a.risk >= HIGH and a.plugin_id not in ignored]


def main(report_path: Path = REPORT, rules_path: Path = RULES) -> int:
    """Print every alert and return 1 if any High-risk alert is not accepted."""
    if not report_path.is_file():
        print(f"::error::ZAP report {report_path} is missing.", file=sys.stderr)
        return 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    ignored = ignored_plugins(rules_path.read_text(encoding="utf-8"))
    found = alerts(report)

    for alert in sorted(found, key=lambda a: -a.risk):
        state = " (accepted in rules.tsv)" if alert.plugin_id in ignored else ""
        print(
            f"{RISK_NAMES.get(alert.risk, alert.risk)}: {alert.name} "
            f"[{alert.plugin_id}] x{alert.instances}{state}"
        )
    failures = blocking(found, ignored)
    for alert in failures:
        print(
            f"::error::ZAP High-risk alert {alert.name} [{alert.plugin_id}]. "
            "Fix it, or accept a false positive in .zap/rules.tsv with a reason."
        )
    if not failures:
        print(f"ZAP gate passed: {len(found)} alert(s), none High-risk and unaccepted.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
