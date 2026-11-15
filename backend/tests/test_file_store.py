# AI contribution: 50% or more AI-generated
"""File store adapter tests (T-03.18.2): the contract, the test fake and Azure Blob."""

import re
from types import SimpleNamespace
from typing import Any, cast

import pytest
from azure.core.exceptions import (
    ResourceExistsError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.storage.blob import ContainerClient
from django.conf import settings
from django.test import override_settings

from adapters.file_store.azure_blob import AzureBlobFileStore, from_settings
from adapters.file_store.base import (
    FileStoreUnavailable,
    StoredFile,
    StoredFileMissing,
)
from adapters.file_store.memory import InMemoryFileStore
from adapters.file_store.registry import configured_store

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


def test_the_test_settings_store_keeps_files_in_memory() -> None:
    """Tests never reach Azure: the store the test settings configure is the fake."""
    InMemoryFileStore.clear()
    store = configured_store(settings.FILE_STORE_BACKEND)

    reference = store.put(
        b"%PDF-1", content_type="application/pdf", prefix="income-notices"
    )

    assert isinstance(store, InMemoryFileStore)
    assert InMemoryFileStore.references() == [reference]
    assert store.read(reference) == StoredFile(b"%PDF-1", "application/pdf")


class StubContainer:
    """Stands in for azure.storage.blob.ContainerClient; records each call."""

    def __init__(self, fail_with: Exception | None = None) -> None:
        self.fail_with = fail_with
        self.blobs: dict[str, tuple[bytes, str]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.create_error: Exception | None = None
        self.public_access: str | None = None

    def _call(self, operation: str, /, **kwargs: Any) -> None:
        self.calls.append((operation, kwargs))
        if self.fail_with is not None:
            raise self.fail_with

    def create_container(self) -> None:
        self._call("create_container")
        if self.create_error is not None:
            raise self.create_error

    def get_container_access_policy(self) -> dict[str, Any]:
        self._call("get_container_access_policy")
        return {"public_access": self.public_access, "signed_identifiers": []}

    def upload_blob(self, name: str, data: bytes, **kwargs: Any) -> None:
        self._call("upload_blob", name=name, **kwargs)
        self.blobs[name] = (data, kwargs["content_settings"].content_type)

    def download_blob(self, blob: str) -> SimpleNamespace:
        self._call("download_blob", blob=blob)
        if blob not in self.blobs:
            raise ResourceNotFoundError("missing")
        content, content_type = self.blobs[blob]
        return SimpleNamespace(
            readall=lambda: content,
            properties=SimpleNamespace(
                content_settings=SimpleNamespace(content_type=content_type)
            ),
        )

    def delete_blob(self, blob: str) -> None:
        self._call("delete_blob", blob=blob)
        if self.blobs.pop(blob, None) is None:
            raise ResourceNotFoundError("missing")


def _calls(container: StubContainer, operation: str) -> list[dict[str, Any]]:
    return [kwargs for call, kwargs in container.calls if call == operation]


def _store(container: StubContainer) -> AzureBlobFileStore:
    return AzureBlobFileStore(cast(ContainerClient, container))


def test_azure_put_uploads_privately_without_overwrite() -> None:
    container = StubContainer()

    reference = _store(container).put(
        b"\x89PNG", content_type="image/png", prefix="income-notices"
    )

    assert REFERENCE.match(reference)
    (upload,) = _calls(container, "upload_blob")
    assert upload["name"] == reference
    assert upload["overwrite"] is False
    assert upload["content_settings"].content_type == "image/png"
    assert len(_calls(container, "create_container")) == 1


def test_azure_put_tolerates_existing_container() -> None:
    container = StubContainer()
    container.create_error = ResourceExistsError("exists")
    store = _store(container)

    store.put(b"a", content_type="image/png", prefix="income-notices")
    store.put(b"b", content_type="image/png", prefix="income-notices")

    assert len(_calls(container, "create_container")) == 1
    assert len(_calls(container, "upload_blob")) == 2


@pytest.mark.parametrize("access", ["blob", "container"])
def test_azure_put_refuses_an_existing_public_container(access: str) -> None:
    container = StubContainer()
    container.create_error = ResourceExistsError("exists")
    container.public_access = access

    with pytest.raises(FileStoreUnavailable, match="must be private"):
        _store(container).put(b"a", content_type="image/png", prefix="income-notices")

    assert _calls(container, "upload_blob") == []


def test_azure_read_returns_content_and_type() -> None:
    store = _store(StubContainer())
    reference = store.put(b"%PDF-1", content_type="application/pdf", prefix="n")

    assert store.read(reference) == StoredFile(b"%PDF-1", "application/pdf")


def test_azure_read_missing_blob_raises_stored_file_missing() -> None:
    with pytest.raises(StoredFileMissing):
        _store(StubContainer()).read("income-notices/" + "0" * 32)


@pytest.mark.parametrize("operation", ["put", "read", "delete"])
def test_azure_errors_become_file_store_unavailable(operation: str) -> None:
    store = _store(StubContainer(fail_with=ServiceRequestError("down")))
    calls = {
        "put": lambda: store.put(b"a", content_type="image/png", prefix="n"),
        "read": lambda: store.read("n/" + "0" * 32),
        "delete": lambda: store.delete("n/" + "0" * 32),
    }

    with pytest.raises(FileStoreUnavailable) as caught:
        calls[operation]()

    assert isinstance(caught.value.__cause__, ServiceRequestError)


def test_azure_delete_ignores_missing_blob() -> None:
    container = StubContainer()

    _store(container).delete("income-notices/" + "0" * 32)

    assert len(_calls(container, "delete_blob")) == 1


@pytest.mark.parametrize(
    "missing",
    ["AZURE_STORAGE_CONNECTION_STRING", "AZURE_STORAGE_CONTAINER_NAME"],
)
def test_from_settings_requires_connection_and_container(missing: str) -> None:
    configured = {
        "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true",
        "AZURE_STORAGE_CONTAINER_NAME": "iris-test",
    }
    with (
        override_settings(**{**configured, missing: ""}),
        pytest.raises(FileStoreUnavailable),
    ):
        from_settings()


def test_from_settings_builds_a_store_for_the_container() -> None:
    with override_settings(
        AZURE_STORAGE_CONNECTION_STRING="UseDevelopmentStorage=true",
        AZURE_STORAGE_CONTAINER_NAME="iris-test",
    ):
        store = from_settings()

    assert isinstance(store, AzureBlobFileStore)


def test_memory_store_lists_its_references() -> None:
    store = InMemoryFileStore()
    reference = store.put(b"x", content_type="image/png", prefix="income-notices")

    assert InMemoryFileStore.references() == [reference]


def test_configured_store_is_built_once_per_backend() -> None:
    backend = "adapters.file_store.memory.InMemoryFileStore"

    assert configured_store(backend) is configured_store(backend)


def test_configured_store_requires_a_backend() -> None:
    with pytest.raises(FileStoreUnavailable):
        configured_store("")


def test_from_settings_rejects_a_malformed_connection_string() -> None:
    with (
        override_settings(
            AZURE_STORAGE_CONNECTION_STRING="not a connection string",
            AZURE_STORAGE_CONTAINER_NAME="iris-test",
        ),
        pytest.raises(FileStoreUnavailable),
    ):
        from_settings()
