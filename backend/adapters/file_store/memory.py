# AI contribution: 50% or more AI-generated
"""In-memory file store: the test fake, shared by every instance in the process."""

from typing import ClassVar
from uuid import uuid4

from adapters.file_store.base import StoredFile, StoredFileMissing


class InMemoryFileStore:
    _objects: ClassVar[dict[str, StoredFile]] = {}

    @classmethod
    def clear(cls) -> None:
        cls._objects.clear()

    @classmethod
    def references(cls) -> list[str]:
        """What is stored now, so tests can check that nothing was left behind."""
        return list(cls._objects)

    def put(self, content: bytes, *, content_type: str, prefix: str) -> str:
        reference = f"{prefix}/{uuid4().hex}"
        self._objects[reference] = StoredFile(bytes(content), content_type)
        return reference

    def read(self, reference: str) -> StoredFile:
        try:
            return self._objects[reference]
        except KeyError as exc:
            raise StoredFileMissing(reference) from exc

    def delete(self, reference: str) -> None:
        self._objects.pop(reference, None)
