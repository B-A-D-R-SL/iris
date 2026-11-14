# AI contribution: 50% or more AI-generated
"""Regenerate postal-folding character classes with the backend's Python runtime."""

import unicodedata
from collections.abc import Callable
from pathlib import Path


def escape(codepoint: int) -> str:
    return rf"\u{{{codepoint:x}}}"


def character_ranges(matches: Callable[[str], bool]) -> list[str]:
    ranges: list[list[int]] = []
    for codepoint in range(0x110000):
        if matches(chr(codepoint)):
            if ranges and ranges[-1][1] + 1 == codepoint:
                ranges[-1][1] = codepoint
            else:
                ranges.append([codepoint, codepoint])
    return [
        escape(start) + ("" if start == end else "-" + escape(end))
        for start, end in ranges
    ]


combining = "".join(character_ranges(lambda value: bool(unicodedata.combining(value))))
unassigned = "".join(
    character_ranges(lambda value: unicodedata.category(value) == "Cn")
)
target = Path(__file__).resolve().parents[1] / "src/shared/forms/unicodeCombining.ts"
target.write_text(
    "// AI contribution: 50% or more AI-generated\n"
    "// Generated with the backend Python runtime: python frontend/scripts/generate-unicode-combining.py\n"
    f"// Unicode {unicodedata.unidata_version}; preserve CCC0 marks and reject newer unassigned characters.\n"
    f"export const COMBINING_MARK =\n  /[{combining}]/gu;\n"
    "export const PYTHON_UNASSIGNED =\n"
    "  // eslint-disable-next-line no-misleading-character-class -- Generated set tests independent codepoints, including marks.\n"
    f"  /[{unassigned}]/u;\n"
)
