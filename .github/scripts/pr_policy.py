# AI contribution: 50% or more AI-generated
"""PR policy check (FIX-26): the pull request format the course rubric grades.

Run by .github/workflows/pr-policy.yml as

    python3 .github/scripts/pr_policy.py --repo OWNER/NAME --pr NUMBER

with GITHUB_TOKEN set. It reads the pull request through the GitHub API and never
checks out or runs its code. The rules are pure functions, tested in test_pr_policy.py.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

LEVELS = (
    "No substantial AI-generated code",
    "Below 50% AI-generated",
    "50% or more AI-generated",
)
NO_AI = LEVELS[0]

# The same IDs the commit-msg hook accepts.
ID = r"(?:T-\d{2}\.\d{2}\.\d+|SET-\d{2}(?:\.\d+)?|FIX-\d{2}(?:\.\d+)?|US-\d+|ES-\d+)"
TITLE = re.compile(rf"^\[PR\] {ID}(?:, {ID})*: \S")

# Dependency bots open pull requests without the team's description sections.
EXEMPT_AUTHORS = frozenset({"dependabot[bot]", "renovate[bot]", "github-actions[bot]"})

# The AI contribution line must sit near the top of the file (after a shebang or docstring).
HEADER_LINES = 10

SOURCE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".css", ".html", ".sh")
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".mjs", ".cjs")
CODE_ROOTS = (
    "backend/",
    "frontend/src/",
    "frontend/scripts/",
    "tools/",
    ".github/scripts/",
)
GENERATED = re.compile(
    r"(^|/)migrations/|(^|/)generated\.d\.ts$|(^|/)mock-data/|/results/|\.lock$|-lock\.(json|yaml)$"
)
TEST = re.compile(
    r"(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$|\.(test|spec)\.[cm]?[jt]sx?$"
)

COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s")
ISSUE_REF = re.compile(r"(?<![\w/&])#\d+\b")
NO_TESTS = "no tests:"
LISTED_PATH = re.compile(r"`([^`\s]+)`|^[ \t]*[-*][ \t]+([^\s`]+)[ \t]*$", re.MULTILINE)


@dataclass
class ChangedFile:
    path: str
    status: str  # GitHub's status: added, modified, removed, renamed, ...
    text: str | None = None  # contents at the head commit; None when not fetched


@dataclass
class PullRequest:
    title: str
    body: str
    author: str
    base: str
    default_branch: str
    closing: list[int] = field(default_factory=list)
    files: list[ChangedFile] = field(default_factory=list)


def visible(body: str | None) -> str:
    """The description without HTML comments, which GitHub does not render."""
    return COMMENT.sub("", body or "")


def is_source(path: str) -> bool:
    """A file the team writes, which must carry an AI contribution line."""
    if GENERATED.search(path):
        return False
    name = path.rsplit("/", 1)[-1]
    if (
        name == "Dockerfile"
        or path.startswith(".githooks/")
        or path == "docker-compose.yml"
    ):
        return True
    if path.startswith(".github/workflows/"):
        return path.endswith((".yml", ".yaml"))
    return path.endswith(SOURCE_SUFFIXES)


def is_test(path: str) -> bool:
    return bool(TEST.search(path))


def needs_tests(path: str) -> bool:
    """Application or tool code whose change should come with a test change."""
    return (
        path.startswith(CODE_ROOTS)
        and path.endswith(CODE_SUFFIXES)
        and not is_test(path)
        and not GENERATED.search(path)
    )


def check_title(title: str) -> list[str]:
    if TITLE.match(title):
        return []
    return [
        (
            "Title must be `[PR] <ID>: <summary>`, for example `[PR] US-17: Walk-in registration` "
            f"(IDs like T-05.33.3, SET-17, FIX-03, US-17, ES-01). Now: `{title}`"
        )
    ]


def check_link(pr: PullRequest) -> list[str]:
    if pr.base == pr.default_branch:
        if pr.closing:
            return []
        return [
            (
                "Close the issue this pull request finishes: add `Closes #<issue>` to the "
                "description. `Refs` or `Part of` does not link it."
            )
        ]
    if ISSUE_REF.search(visible(pr.body)):
        return []
    return [
        f"Reference the issue this pull request works on (`#<issue>`); it targets `{pr.base}`."
    ]


def ai_section(body: str | None) -> str | None:
    """The AI contribution section, up to the next heading of the same or a higher level."""
    lines = visible(body).splitlines()
    starts = [i for i, line in enumerate(lines) if "ai contribution" in line.lower()]
    if not starts:
        return None
    headings = [i for i in starts if HEADING.match(lines[i])]
    start = headings[0] if headings else starts[0]
    match = HEADING.match(lines[start])
    level = len(match.group(1)) if match else 7
    end = len(lines)
    for j in range(start + 1, len(lines)):
        other = HEADING.match(lines[j])
        if other and len(other.group(1)) <= level:
            end = j
            break
    return "\n".join(lines[start:end])


def listed_paths(section: str) -> list[str]:
    return [a or b for a, b in LISTED_PATH.findall(section)]


def lists_changed_file(listed: list[str], changed: list[str]) -> bool:
    for path in listed:
        if path in changed:
            return True
        if path.endswith("/") and any(c.startswith(path) for c in changed):
            return True
    return False


def check_ai(pr: PullRequest) -> list[str]:
    section = ai_section(pr.body)
    if section is None:
        return ["Add an `## AI contribution` section (see the pull request template)."]
    found = [level for level in LEVELS if level.lower() in section.lower()]
    if len(found) != 1:
        return [
            "The AI contribution section must give exactly one level: "
            + ", ".join(f"`{level}`" for level in LEVELS)
            + f". Found {len(found)}."
        ]
    if found[0] == NO_AI:
        return []
    changed = [f.path for f in pr.files]
    if lists_changed_file(listed_paths(section), changed):
        return []
    return [
        (
            "List the AI-assisted files under the AI contribution section, one changed path per line "
            "(for example `- backend/modules/listings/services.py`)."
        )
    ]


def has_declaration(text: str) -> bool:
    head = "\n".join(text.splitlines()[:HEADER_LINES]).lower()
    return any(level.lower() in head for level in LEVELS)


def check_headers(pr: PullRequest) -> list[str]:
    missing = [
        f.path
        for f in pr.files
        if f.status != "removed"
        and is_source(f.path)
        and f.text is not None
        and f.text.strip()
        and not has_declaration(f.text)
    ]
    if not missing:
        return []
    return [
        "Start each of these files with its AI contribution line (one of the three levels) "
        "in its first 10 lines: " + ", ".join(f"`{path}`" for path in missing)
    ]


def explains_missing_tests(body: str | None) -> bool:
    """True when a visible line starts with "No tests:" and gives a reason."""
    for line in visible(body).splitlines():
        text = line.strip().lstrip("-*").strip().replace("**", "")
        if text.lower().startswith(NO_TESTS) and text[len(NO_TESTS) :].strip():
            return True
    return False


def check_tests(pr: PullRequest) -> list[str]:
    code = [f.path for f in pr.files if f.status != "removed" and needs_tests(f.path)]
    if not code or any(is_test(f.path) for f in pr.files):
        return []
    if explains_missing_tests(pr.body):
        return []
    return [
        (
            f"Code changed ({len(code)} files, for example `{code[0]}`) but no test file did. "
            "Add or change a test, or explain why in a line starting with `No tests:`."
        )
    ]


def evaluate(pr: PullRequest) -> list[str]:
    if pr.author in EXEMPT_AUTHORS:
        return []
    return (
        check_title(pr.title)
        + check_link(pr)
        + check_ai(pr)
        + check_headers(pr)
        + check_tests(pr)
    )


def annotation(message: str) -> str:
    """A GitHub Actions error annotation, with the characters it reserves escaped."""
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return f"::error title=PR policy::{escaped}"


class GitHub:
    """The few read-only GitHub API calls the check needs."""

    API = "https://api.github.com"

    def __init__(self, token: str) -> None:
        self.token = token

    def _get(
        self,
        url: str,
        accept: str = "application/vnd.github+json",
        data: bytes | None = None,
    ) -> bytes:
        request = urllib.request.Request(
            url, data=data, method="POST" if data else "GET"
        )
        request.add_header("Authorization", f"Bearer {self.token}")
        request.add_header("Accept", accept)
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()

    def json(self, path: str) -> dict | list:
        return json.loads(self._get(f"{self.API}{path}"))

    def closing_issues(self, repo: str, number: int) -> list[int]:
        owner, name = repo.split("/", 1)
        query = (
            "query($owner: String!, $name: String!, $number: Int!) { repository(owner: $owner, name: $name) "
            "{ pullRequest(number: $number) { closingIssuesReferences(first: 50) { nodes { number } } } } }"
        )
        payload = json.dumps(
            {
                "query": query,
                "variables": {"owner": owner, "name": name, "number": number},
            }
        )
        result = json.loads(self._get(f"{self.API}/graphql", data=payload.encode()))
        if result.get("errors"):
            raise RuntimeError(f"GraphQL error: {result['errors']}")
        nodes = result["data"]["repository"]["pullRequest"]["closingIssuesReferences"][
            "nodes"
        ]
        return [node["number"] for node in nodes]

    def files(self, repo: str, number: int) -> list[dict]:
        files: list[dict] = []
        for page in range(1, 31):  # the API returns at most 3,000 files
            batch = self.json(
                f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}"
            )
            files.extend(batch)
            if len(batch) < 100:
                break
        return files

    def text(self, repo: str, path: str, ref: str) -> str:
        quoted = urllib.parse.quote(path, safe="/")
        raw = self._get(
            f"{self.API}/repos/{repo}/contents/{quoted}?ref={ref}",
            accept="application/vnd.github.raw",
        )
        return raw.decode("utf-8", errors="replace")


def load(github: GitHub, repo: str, number: int) -> PullRequest:
    data = github.json(f"/repos/{repo}/pulls/{number}")
    head_repo = data["head"]["repo"]["full_name"] if data["head"]["repo"] else repo
    files = []
    for item in github.files(repo, number):
        changed = ChangedFile(path=item["filename"], status=item["status"])
        if changed.status != "removed" and is_source(changed.path):
            changed.text = github.text(head_repo, changed.path, data["head"]["sha"])
        files.append(changed)
    return PullRequest(
        title=data["title"],
        body=data["body"] or "",
        author=data["user"]["login"],
        base=data["base"]["ref"],
        default_branch=data["base"]["repo"]["default_branch"],
        closing=github.closing_issues(repo, number),
        files=files,
    )


def report(errors: list[str], number: int) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [f"## PR policy: #{number}", ""]
    lines += (
        [f"- {error}" for error in errors]
        if errors
        else ["Everything the policy checks is in place."]
    )
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    for error in errors:
        print(annotation(error))
    if not errors:
        print("PR policy passed.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo", default=os.environ.get("GITHUB_REPOSITORY"), required=False
    )
    parser.add_argument("--pr", type=int, required=True)
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token or not args.repo:
        print(
            "::error title=PR policy::GITHUB_TOKEN and --repo (or GITHUB_REPOSITORY) are required."
        )
        return 2
    try:
        pr = load(GitHub(token), args.repo, args.pr)
    except (
        OSError,
        RuntimeError,
        KeyError,
        ValueError,
    ) as exc:  # URLError is an OSError
        print(
            annotation(
                f"Could not read pull request #{args.pr} from GitHub ({type(exc).__name__}: {exc}). Re-run the check."
            )
        )
        return 2
    if pr.author in EXEMPT_AUTHORS:
        print(f"PR policy skipped: opened by {pr.author}.")
        return 0
    errors = evaluate(pr)
    report(errors, args.pr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
