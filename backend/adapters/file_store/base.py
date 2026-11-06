# AI contribution: 50% or more AI-generated
"""Contract for private file storage, separate from business modules (review rule 9)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredFile:
    content: bytes
    content_type: str


class FileStoreUnavailable(Exception):
    """The storage service is not configured or cannot be reached."""


class StoredFileMissing(Exception):
    """No stored file has this reference."""


class FileStore(Protocol):
    """Stores files privately and returns opaque references, never URLs.

    A reference has the form ``<prefix>/<random hex>`` and contains no
    personal data or uploaded file name.
    """

    def put(self, content: bytes, *, content_type: str, prefix: str) -> str: ...

    def read(self, reference: str) -> StoredFile: ...

    def delete(self, reference: str) -> None: ...
