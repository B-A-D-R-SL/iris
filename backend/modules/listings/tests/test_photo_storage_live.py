# AI contribution: 50% or more AI-generated
"""Opt-in HTTP/DB/Azurite integration; all records and images are synthetic."""

import os
from collections.abc import Iterator
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from azure.storage.blob import BlobClient, BlobServiceClient
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from adapters.blob_photos import STORAGE_API_VERSION, BlobPhotoStore
from modules.listings import photo_storage, services
from modules.listings.models import Listing
from modules.listings.tests.test_photo_upload import payload, upload

pytestmark = pytest.mark.skipif(
    os.environ.get("IRIS_TEST_AZURITE") != "1",
    reason="Opt-in real Azurite integration",
)


@pytest.fixture
def actual_store(settings: Any) -> Iterator[BlobPhotoStore]:
    settings.AZURE_STORAGE_CONTAINER_NAME = "iris-post-tests-" + uuid4().hex
    settings.AZURE_STORAGE_ALLOW_HTTP = True
    # This test runs inside Docker; real browser links are covered separately.
    settings.AZURE_STORAGE_PUBLIC_BLOB_ENDPOINT = ""
    store = photo_storage.configured_store()
    try:
        yield store
    finally:
        with BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING,
            api_version=STORAGE_API_VERSION,
        ) as client:
            container = client.get_container_client(
                settings.AZURE_STORAGE_CONTAINER_NAME
            )
            if container.exists():
                container.delete_container()


def test_actual_post_endpoint_saves_processed_photo_in_private_storage(
    posting_case: SimpleNamespace,
    actual_store: BlobPhotoStore,
) -> None:
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_authenticate(user=posting_case.user)
    response = client.post(
        reverse("store-listing-create"),
        payload(posting_case, upload()),
        format="multipart",
    )
    assert response.status_code == 201
    listing = Listing.objects.get(pk=response.json()["id"])
    assert listing.photo_ref is not None
    link = actual_store.read_link(listing.photo_ref)
    with BlobClient.from_blob_url(link.url, api_version=STORAGE_API_VERSION) as blob:
        content = blob.download_blob().readall()
        assert (
            blob.get_blob_properties().content_settings.cache_control
            == "private, no-store"
        )
    with Image.open(BytesIO(content)) as image:
        image.load()
        assert image.size == (1280, 640)
        assert not image.getexif()


def test_database_failure_leaves_no_actual_blob(
    posting_case: SimpleNamespace,
    actual_store: BlobPhotoStore,
    monkeypatch: pytest.MonkeyPatch,
    settings: Any,
) -> None:
    def fail_save(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("synthetic database failure")

    monkeypatch.setattr(Listing, "save", fail_save)
    photo = upload()
    with pytest.raises(RuntimeError, match="synthetic database failure"):
        services.post_listing(
            posting_case.store.pk, posting_case.user, posting_case.data, photo=photo
        )
    assert not Listing.objects.exists()
    with BlobServiceClient.from_connection_string(
        settings.AZURE_STORAGE_CONNECTION_STRING,
        api_version=STORAGE_API_VERSION,
    ) as client:
        assert (
            list(
                client.get_container_client(
                    settings.AZURE_STORAGE_CONTAINER_NAME
                ).list_blobs()
            )
            == []
        )
