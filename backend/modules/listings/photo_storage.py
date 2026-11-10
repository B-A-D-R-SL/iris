# AI contribution: 50% or more AI-generated
"""Construct the configured storage adapter; no network access during startup."""

from typing import cast

from django.conf import settings
from django.utils.module_loading import import_string

from adapters.blob_photos import (
    BlobPhotoConfig,
    BlobPhotoStore,
    config_from_connection_string,
)
from adapters.photo_types import PhotoStorageError
from modules.listings.contracts import ListingPhotoStore


def configured_store() -> BlobPhotoStore:
    """Build the Azure adapter from Django settings without opening a connection."""
    options = {
        "container": settings.AZURE_STORAGE_CONTAINER_NAME,
        "public_endpoint": settings.AZURE_STORAGE_PUBLIC_BLOB_ENDPOINT,
        "allow_http": settings.AZURE_STORAGE_ALLOW_HTTP,
        "max_pixels": settings.LISTING_PHOTO_MAX_PIXELS,
    }
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        config = config_from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING, **options
        )
    else:
        config = BlobPhotoConfig(
            account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
            account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
            account_url=settings.AZURE_STORAGE_BLOB_ENDPOINT
            or (f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"),
            **options,
        )
    return BlobPhotoStore(config)


def load_store() -> ListingPhotoStore:
    """Use the same configured factory for uploads and reads."""
    backend = settings.LISTING_PHOTO_STORE_BACKEND
    if not backend:
        raise PhotoStorageError("Listing photo storage is not available yet.")
    try:
        return cast(ListingPhotoStore, import_string(backend)())
    except (ImportError, AttributeError, ValueError, PhotoStorageError):
        raise PhotoStorageError("Photo storage is temporarily unavailable.") from None


def read_urls(references: list[str]) -> dict[str, str]:
    """Sign only references from an authorized page, without initializing on empty pages."""
    if not references:
        return {}
    return {
        reference: link.url
        for reference, link in load_store().read_links(references).items()
    }
