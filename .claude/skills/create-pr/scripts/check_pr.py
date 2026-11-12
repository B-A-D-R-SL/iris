# AI contribution: 50% or more AI-generated
"""Run the PR policy rules locally, before the pull request exists.

Uses the same pure functions as .github/scripts/pr_policy.py, but builds the pull
request from local git instead of the GitHub API:

    py .claude/skills/create-pr/scripts/check_pr.py --base main \
        --title "[PR] US-41: Reserve a unit" --body-file <path>

Changed files are `git diff <origin/base>...HEAD` (what GitHub shows on the PR), read
at HEAD. Closing issues are parsed from the description with GitHub's closing keywords,
because the GraphQL link only exists once the PR is open. Exit 0 when nothing fails.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(
    subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
)
sys.path.insert(0, str(ROOT / ".github" / "scripts"))

import pr_policy  # noqa: E402

# GitHub links these keywords to an issue only when the PR targets the default branch.
CLOSING = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)\b", re.IGNORECASE
)
STATUS = {"A": "added", "M": "modified", "D": "removed", "R": "renamed", "C": "copied"}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout


def default_branch() -> str:
    try:
        ref = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD").strip()
        return ref.split("/", 1)[1]
    except subprocess.CalledProcessError:
        return "main"


def changed_files(base_ref: str) -> list[pr_policy.ChangedFile]:
    files = []
    for line in git("diff", "--name-status", "-M", f"{base_ref}...HEAD").splitlines():
        parts = line.split("\t")
        status = STATUS.get(parts[0][0], "modified")
        path = parts[-1]
        changed = pr_policy.ChangedFile(path=path, status=status)
        if status != "removed" and pr_policy.is_source(path):
            changed.text = git("show", f"HEAD:{path}")
        files.append(changed)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="target branch, e.g. main")
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args()

    body = args.body_file.read_text(encoding="utf-8")
    base_ref = f"{args.remote}/{args.base}"
    pr = pr_policy.PullRequest(
        title=args.title,
        body=body,
        author="local",
        base=args.base,
        default_branch=default_branch(),
        closing=[int(n) for n in CLOSING.findall(pr_policy.visible(body))],
        files=changed_files(base_ref),
    )
    errors = pr_policy.evaluate(pr)
    print(f"{len(pr.files)} changed files against {base_ref}")
    for error in errors:
        print(f"FAIL: {error}")
    if not errors:
        print("PR policy (local): everything passes.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
