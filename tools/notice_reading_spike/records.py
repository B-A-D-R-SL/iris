# AI contribution: 50% or more AI-generated
"""The per-file result of a benchmark run, shared by the run loop and the scorer."""

from __future__ import annotations

from dataclasses import dataclass

from reader import NoticeReading


@dataclass(frozen=True)
class RunRecord:
    """What one reader returned for one file."""

    file: str
    reading: NoticeReading | None
    seconds: float
    error: str | None
    cost_usd: float
