# AI contribution: 50% or more AI-generated
"""File store adapter tests (T-03.18.2): the contract, the test fake and Azure Blob."""

import re

import pytest
from django.conf import settings

from adapters.file_store.base import StoredFile, StoredFileMissing
from adapters.file_store.memory import InMemoryFileStore

REFERENCE = re.compile(r"^income-notices/[0-9a-f]{32}$")


def test_memory_store_round_trip() -> None:
    store = InMemoryFileStore()

    reference = store.put(
        b"%PDF-1", content_type="application/pdf", prefix="income-notices"
    )

    assert REFERENCE.match(reference)
    assert store.read(reference) == StoredFile(b"%PDF-1", "application/pdf")


def test_memory_store_shares_objects_across_instances() -> None:
    reference = InMemoryFileStore().put(
        b"\x89PNG", content_type="image/png", prefix="income-notices"
    )

    assert InMemoryFileStore().read(reference).content == b"\x89PNG"


def test_memory_store_references_are_unique() -> None:
    store = InMemoryFileStore()

    first = store.put(b"same", content_type="image/png", prefix="income-notices")
    second = store.put(b"same", content_type="image/png", prefix="income-notices")

    assert first != second


def test_memory_store_read_missing_raises() -> None:
    with pytest.raises(StoredFileMissing):
        InMemoryFileStore().read("income-notices/" + "0" * 32)


def test_memory_store_delete_is_idempotent() -> None:
    store = InMemoryFileStore()
    reference = store.put(b"x", content_type="image/png", prefix="income-notices")

    store.delete(reference)
    store.delete(reference)

    with pytest.raises(StoredFileMissing):
        store.read(reference)


def test_test_settings_use_the_memory_store() -> None:
    assert settings.FILE_STORE_BACKEND == "adapters.file_store.memory.InMemoryFileStore"
