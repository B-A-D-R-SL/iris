# AI contribution: 50% or more AI-generated
"""The configured file store, built once per process and backend path."""

from functools import cache
from typing import cast

from django.utils.module_loading import import_string

from adapters.file_store.base import FileStore, FileStoreUnavailable


@cache
def configured_store(backend: str) -> FileStore:
    """The store named by a FILE_STORE_BACKEND path (a zero-argument callable).

    Reusing one store keeps one storage client and connection pool per process,
    and its container is checked once. A failure is not cached, so a later call
    tries again.
    """
    if not backend:
        raise FileStoreUnavailable("No file store is configured.")
    return cast(FileStore, import_string(backend)())
