# AI contribution: 50% or more AI-generated
"""A fake reader that returns each mock notice's truth; US-22's FakeDocumentReader."""

from __future__ import annotations

import hashlib
from pathlib import Path

from reader import DocumentReadError, NoticeReading, ReadField
from score import TruthRow


class TruthReader:
    """Identifies a notice by the SHA-256 of its bytes and returns its truth at confidence 1.0."""

    def __init__(self, truth: dict[str, TruthRow], notices_dir: Path) -> None:
        self.last_cost_usd = 0.0
        self._by_hash = {
            hashlib.sha256((notices_dir / name).read_bytes()).hexdigest(): row
            for name, row in truth.items()
        }

    def read_notice(self, content: bytes, content_type: str) -> NoticeReading:
        row = self._by_hash.get(hashlib.sha256(content).hexdigest())
        if row is None:
            raise DocumentReadError("unknown document")
        values = row.expected
        return NoticeReading(**{name: ReadField(value, 1.0) for name, value in values.items()})
