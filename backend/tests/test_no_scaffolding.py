# AI contribution: 50% or more AI-generated
"""Modules hold no placeholder files (FIX-06, Code Quality Rubric 3.8).

A module adds a file when the story that needs it starts, so no file may hold
only a docstring, and no module code may carry a TODO.
"""

import ast
from pathlib import Path

MODULES = Path(__file__).resolve().parent.parent / "modules"


def _module_sources() -> list[Path]:
    return sorted(
        path for path in MODULES.rglob("*.py") if "migrations" not in path.parts
    )


def test_no_file_holds_only_a_docstring() -> None:
    placeholders = [
        path.relative_to(MODULES).as_posix()
        for path in _module_sources()
        if path.name != "__init__.py"
        and all(
            isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            for node in ast.parse(path.read_text(encoding="utf-8")).body
        )
    ]

    assert placeholders == []


def test_no_module_code_carries_a_todo() -> None:
    todos = [
        f"{path.relative_to(MODULES).as_posix()}:{number}"
        for path in _module_sources()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "TODO" in line
    ]

    assert todos == []
