# AI contribution: 50% or more AI-generated
"""Provider-independent photo storage results and failures."""

from dataclasses import dataclass, field
from datetime import datetime


class PhotoStorageError(RuntimeError):
    """Storage is unavailable; provider messages and credentials remain private."""


@dataclass(frozen=True)
class PhotoReadLink:
    url: str = field(repr=False)
    expires_at: datetime
