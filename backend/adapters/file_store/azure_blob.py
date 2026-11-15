# AI contribution: 50% or more AI-generated
"""Private Azure Blob Storage (Azurite in development) behind the FileStore contract."""

from uuid import uuid4

from azure.core.exceptions import AzureError, ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import ContainerClient, ContentSettings
from django.conf import settings

from adapters.file_store.base import (
    FileStoreUnavailable,
    StoredFile,
    StoredFileMissing,
)


class AzureBlobFileStore:
    """Stores each file as a new blob in one private container.

    Blobs are never overwritten. The container is created without public
    access the first time a file is stored, and an existing container is
    refused unless it is private.
    """

    def __init__(self, container: ContainerClient) -> None:
        self._container = container
        self._container_ready = False

    def put(self, content: bytes, *, content_type: str, prefix: str) -> str:
        reference = f"{prefix}/{uuid4().hex}"
        try:
            self._ensure_container()
            self._container.upload_blob(
                name=reference,
                data=content,
                overwrite=False,
                content_settings=ContentSettings(content_type=content_type),
            )
        except AzureError as exc:
            raise FileStoreUnavailable("The file could not be stored.") from exc
        return reference

    def read(self, reference: str) -> StoredFile:
        try:
            downloader = self._container.download_blob(reference)
            content = downloader.readall()
        except ResourceNotFoundError as exc:
            raise StoredFileMissing(reference) from exc
        except AzureError as exc:
            raise FileStoreUnavailable("The file could not be read.") from exc
        content_type = downloader.properties.content_settings.content_type
        return StoredFile(content, content_type or "application/octet-stream")

    def delete(self, reference: str) -> None:
        try:
            self._container.delete_blob(reference)
        except ResourceNotFoundError:
            return
        except AzureError as exc:
            raise FileStoreUnavailable("The file could not be deleted.") from exc

    def _ensure_container(self) -> None:
        if self._container_ready:
            return
        try:
            self._container.create_container()
        except ResourceExistsError:
            pass
        # An existing container keeps its own access level: notices must stay private.
        if self._container.get_container_access_policy().get("public_access"):
            raise FileStoreUnavailable("The notice container must be private.")
        self._container_ready = True


def from_settings() -> AzureBlobFileStore:
    """Build the store from AZURE_STORAGE_CONNECTION_STRING and the container name."""
    connection = settings.AZURE_STORAGE_CONNECTION_STRING
    container = settings.AZURE_STORAGE_CONTAINER_NAME
    if not connection or not container:
        raise FileStoreUnavailable("Azure Blob Storage is not configured.")
    try:
        client = ContainerClient.from_connection_string(connection, container)
    except ValueError as exc:
        raise FileStoreUnavailable("The storage connection string is invalid.") from exc
    return AzureBlobFileStore(client)
