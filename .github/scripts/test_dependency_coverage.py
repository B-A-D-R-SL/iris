# AI contribution: 50% or more AI-generated
"""Every locked project gets Dependabot updates and a dependency audit (FIX-25).

Before FIX-25 the tools/ projects were neither updated nor audited, and their alerts piled
up unnoticed. These tests fail when a project with a lock file is added without being added
to .github/dependabot.yml and .github/workflows/dependency-audit.yml, or when a removed
project is still listed there.

Run: python3 -m unittest discover -s .github/scripts
"""

import subprocess
import unittest
from pathlib import Path

# PyYAML is in the backend environment that runs these tests (drf-spectacular requires it).
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
AUDIT_WORKFLOW = ROOT / ".github" / "workflows" / "dependency-audit.yml"


def locked_projects(lock_name: str) -> set[str]:
    """Folders, relative to the repository root, holding a lock file tracked by Git."""
    listed = subprocess.run(
        ["git", "ls-files", "--", f"*{lock_name}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return {
        Path(path).parent.as_posix() for path in listed if Path(path).name == lock_name
    }


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dependabot_updates(ecosystem: str) -> list[dict]:
    return [
        u for u in load(DEPENDABOT)["updates"] if u["package-ecosystem"] == ecosystem
    ]


def dependabot_directories(ecosystem: str) -> set[str]:
    """Dependabot's "/backend" style directories, as "backend" (the root is ".")."""
    folders: set[str] = set()
    for update in dependabot_updates(ecosystem):
        folders.update(update.get("directories") or [update["directory"]])
    return {folder.strip("/") or "." for folder in folders}


def grouped_update_types(update: dict) -> set[str]:
    """Version update types (major, minor, patch) that one of the update's groups bundles.

    A group without "update-types" bundles all three; security-only groups don't count.
    """
    grouped: set[str] = set()
    for group in update.get("groups", {}).values():
        if group.get("applies-to", "version-updates") == "version-updates":
            grouped.update(group.get("update-types", ["major", "minor", "patch"]))
    return grouped


class DependencyCoverageTest(unittest.TestCase):
    def test_finds_the_uv_projects_tools_included(self):
        # Guards the helper itself: an empty set would make the comparisons below pass.
        self.assertLessEqual(
            {"backend", "tools/mock_notices", "tools/notice_reading_spike"},
            locked_projects("uv.lock"),
        )

    def test_dependabot_updates_exactly_the_uv_projects(self):
        self.assertEqual(dependabot_directories("uv"), locked_projects("uv.lock"))

    def test_dependabot_updates_exactly_the_pnpm_projects(self):
        self.assertEqual(
            dependabot_directories("npm"), locked_projects("pnpm-lock.yaml")
        )

    def test_dependabot_updates_the_github_actions(self):
        self.assertEqual(dependabot_directories("github-actions"), {"."})

    def test_audit_workflow_audits_exactly_the_uv_projects(self):
        matrix = load(AUDIT_WORKFLOW)["jobs"]["python"]["strategy"]["matrix"]["project"]
        self.assertEqual(set(matrix), locked_projects("uv.lock"))

    def test_audit_workflow_audits_frontend_development_dependencies(self):
        steps = load(AUDIT_WORKFLOW)["jobs"]["frontend"]["steps"]
        commands = [step["run"] for step in steps if "run" in step]
        self.assertEqual(commands, ["pnpm audit --audit-level high"])

    def test_every_update_is_weekly_and_groups_minor_and_patch(self):
        for update in load(DEPENDABOT)["updates"]:
            with self.subTest(ecosystem=update["package-ecosystem"]):
                self.assertEqual(update["schedule"]["interval"], "weekly")
                self.assertLessEqual({"minor", "patch"}, grouped_update_types(update))

    def test_grouped_update_types_ignore_security_groups(self):
        # A security-only group must not count as grouping the weekly version updates.
        update = {
            "groups": {
                "security": {"applies-to": "security-updates", "patterns": ["*"]},
                "minor": {"update-types": ["minor"]},
            }
        }
        self.assertEqual(grouped_update_types(update), {"minor"})


if __name__ == "__main__":
    unittest.main()
