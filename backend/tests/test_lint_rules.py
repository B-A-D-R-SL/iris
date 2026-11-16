# AI contribution: 50% or more AI-generated
"""FIX-19: Ruff enforces PEP 8 names and the complexity limit of 15.

Each case lints a small module with the project's own Ruff settings, so a
change to backend/pyproject.toml that drops a rule fails here.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
MAX_COMPLEXITY = 15


def _ruff_codes(source: str) -> set[str]:
    """Rule codes Ruff reports for ``source`` linted as a module's service file."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--output-format=json",
            "--stdin-filename=modules/sample/services.py",
            "-",
        ],
        input=source,
        capture_output=True,
        text=True,
        cwd=BACKEND,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    return {finding["code"] for finding in json.loads(result.stdout)}


def _function_of_complexity(complexity: int) -> str:
    """One path, plus one for each ``if``: cyclomatic complexity ``complexity``."""
    branches = "".join(
        f"    if value == {n}:\n        return {n}\n" for n in range(complexity - 1)
    )
    return f"def choose(value):\n{branches}    return -1\n"


def test_function_at_the_complexity_limit_passes():
    assert _ruff_codes(_function_of_complexity(MAX_COMPLEXITY)) == set()


def test_function_over_the_complexity_limit_fails():
    assert "C901" in _ruff_codes(_function_of_complexity(MAX_COMPLEXITY + 1))


@pytest.mark.parametrize(
    ("source", "code"),
    [
        ("class listing_form:\n    pass\n", "N801"),
        ("def postListing():\n    return 1\n", "N802"),
        ("def post(unitsLeft):\n    return unitsLeft\n", "N803"),
        ("def post():\n    unitsLeft = 1\n    return unitsLeft\n", "N806"),
    ],
)
def test_names_that_break_pep8_fail(source, code):
    assert code in _ruff_codes(source)


def test_exception_named_for_its_condition_passes():
    """Documented exception (wiki Naming Conventions): no Error suffix needed."""
    source = 'class HolderTooYoung(Exception):\n    """Under 18."""\n'
    assert _ruff_codes(source) == set()
