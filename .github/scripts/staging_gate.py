# AI contribution: 50% or more AI-generated
"""Refuse stale, foreign or untested deployments before any Azure access."""

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

REPOSITORY = "B-A-D-R-SL/iris"


def _api(path: str) -> dict:
    request = Request(
        f"https://api.github.com/repos/{REPOSITORY}/{path}",
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def verified_sha(event: dict, event_name: str, sha: str, ref: str) -> str:
    """Use only the current main commit and its latest successful push CI run."""
    if event.get("repository", {}).get("full_name") != REPOSITORY:
        raise ValueError("Deployment repository is not Iris.")
    if event_name == "workflow_run":
        run = event["workflow_run"]
        if (
            run.get("event") != "push"
            or run.get("head_branch") != "main"
            or run.get("head_repository", {}).get("full_name") != REPOSITORY
            or run.get("conclusion") != "success"
        ):
            raise ValueError("Deployment requires successful main push CI.")
        sha = run["head_sha"]
    elif event_name != "workflow_dispatch" or ref != "refs/heads/main":
        raise ValueError("Manual deployments must run from main.")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid deployment revision.")
    if _api("git/ref/heads/main")["object"]["sha"] != sha:
        raise ValueError("Main has moved; deploy its newest successful CI run.")
    runs = _api(
        f"actions/workflows/ci.yml/runs?branch=main&event=push&head_sha={sha}&per_page=1"
    )["workflow_runs"]
    if not runs or runs[0]["head_sha"] != sha or runs[0]["conclusion"] != "success":
        raise ValueError("The latest CI run for this revision must pass first.")
    return sha


def main() -> int:
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        sha = verified_sha(
            event,
            os.environ["GITHUB_EVENT_NAME"],
            os.environ["GITHUB_SHA"],
            os.environ["GITHUB_REF"],
        )
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            output.write(f"sha={sha}\n")
    except (ValueError, KeyError, OSError, URLError):
        print(
            "::error::Deployment gate refused the revision or GitHub was unavailable."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
