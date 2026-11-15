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


def _holds_only_a_docstring(source: str) -> bool:
    """True when the code is nothing but string constants (docstrings)."""
    return all(
        isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
        for node in ast.parse(source).body
    )


def _todo_lines(source: str) -> list[int]:
    return [
        number for number, line in enumerate(source.splitlines(), 1) if "TODO" in line
    ]


def test_no_file_holds_only_a_docstring() -> None:
    placeholders = [
        path.relative_to(MODULES).as_posix()
        for path in _module_sources()
        if path.name != "__init__.py"
        and _holds_only_a_docstring(path.read_text(encoding="utf-8"))
    ]

    assert placeholders == []


def test_no_module_code_carries_a_todo() -> None:
    todos = [
        f"{path.relative_to(MODULES).as_posix()}:{number}"
        for path in _module_sources()
        for number in _todo_lines(path.read_text(encoding="utf-8"))
    ]

    assert todos == []


def test_a_stub_like_the_removed_ones_is_caught() -> None:
    stub = '# AI contribution: 50% or more AI-generated\n"""Tasks.\n\nTODO: add jobs.\n"""\n'

    assert _holds_only_a_docstring(stub) is True
    assert _todo_lines(stub) == [4]


def test_an_empty_file_counts_as_a_placeholder() -> None:
    assert _holds_only_a_docstring("") is True


def test_real_code_and_todo_free_text_pass() -> None:
    code = '"""Queries."""\n\n\ndef active() -> list[str]:\n    return []\n'

    assert _holds_only_a_docstring(code) is False
    assert _todo_lines(code) == []
