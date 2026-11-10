# AI contribution: 50% or more AI-generated
"""Opt-in integration proof against Azurite, using synthetic in-memory images.

These tests intentionally use the real SDK to verify the adapter's security
boundary. Every test owns and finally removes its own dedicated container.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO
from threading import Event, Timer
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import pytest
from azure.core.exceptions import HttpResponseError
from azure.storage.blob import BlobClient, BlobServiceClient
from PIL import Image

from adapters.blob_photos import (
    STORAGE_API_VERSION,
    BlobPhotoStore,
    config_from_connection_string,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("IRIS_TEST_AZURITE") != "1",
    reason="Set IRIS_TEST_AZURITE=1 with the local Azurite connection string",
)


@pytest.fixture
def live_store() -> Iterator[BlobPhotoStore]:
    connection = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    name = "iris-photo-tests-" + uuid4().hex
    config = config_from_connection_string(connection, container=name, allow_http=True)
    store = BlobPhotoStore(config)
    try:
        yield store
    finally:
        with BlobServiceClient.from_connection_string(
            connection, api_version=STORAGE_API_VERSION
        ) as client:
            if client.get_container_client(name).exists():
                client.delete_container(name)


def synthetic_photo() -> bytes:
    with Image.new("RGB", (1800, 900), "green") as image:
        exif = Image.Exif()
        exif[271] = "IRIS SYNTHETIC CAMERA"
        exif[34853] = {1: "N", 2: (45, 0, 0), 3: "W", 4: (73, 0, 0)}
        output = BytesIO()
        image.save(output, format="JPEG", exif=exif)
        return output.getvalue()


def test_batch_links_read_their_own_blobs(live_store: BlobPhotoStore) -> None:
    references = [
        live_store.put_image(synthetic_photo(), max_dimension=1280) for _ in range(2)
    ]
    links = live_store.read_links(references)
    assert set(links) == set(references)
    for reference, link in links.items():
        assert urlsplit(link.url).path.endswith("/" + reference)
        with BlobClient.from_blob_url(
            link.url, api_version=STORAGE_API_VERSION
        ) as blob:
            content = blob.download_blob().readall()
        with Image.open(BytesIO(content)) as image:
            assert image.size == (1280, 640)


def test_private_upload_read_only_link_and_delete(live_store: BlobPhotoStore) -> None:
    reference = live_store.put_image(synthetic_photo(), max_dimension=1280)
    link = live_store.read_link(reference)
    unsigned = link.url.split("?", 1)[0]
    with BlobClient.from_blob_url(
        unsigned, api_version=STORAGE_API_VERSION
    ) as anonymous:
        with pytest.raises(HttpResponseError) as refused:
            anonymous.download_blob()
        assert refused.value.status_code in {403, 404}
    with BlobClient.from_blob_url(link.url, api_version=STORAGE_API_VERSION) as reader:
        content = reader.download_blob().readall()
        with Image.open(BytesIO(content)) as image:
            assert image.size == (1280, 640)
            assert not image.getexif()
        with pytest.raises(HttpResponseError) as write:
            reader.upload_blob(b"unauthorized", overwrite=True)
        assert write.value.status_code == 403
        with pytest.raises(HttpResponseError) as delete:
            reader.delete_blob()
        assert delete.value.status_code == 403
    live_store.delete(reference)
    live_store.delete(reference)
    with BlobClient.from_blob_url(link.url, api_version=STORAGE_API_VERSION) as reader:
        with pytest.raises(HttpResponseError) as missing:
            reader.download_blob()
        assert missing.value.status_code == 404


def test_expired_tampered_and_other_blob_links_are_refused(
    live_store: BlobPhotoStore,
) -> None:
    reference = live_store.put_image(synthetic_photo(), max_dimension=1280)
    other = live_store.put_image(synthetic_photo(), max_dimension=1280)
    valid = live_store.read_link(reference)
    expired = live_store.read_link(
        reference, at=datetime.now(UTC) - timedelta(minutes=6)
    )
    parsed = urlsplit(valid.url)
    query = parse_qs(parsed.query)
    query["se"] = ["2099-01-01T00:00:00Z"]
    tampered = urlunsplit(parsed._replace(query=urlencode(query, doseq=True)))
    changed_blob = valid.url.replace(reference, other)
    for url in (expired.url, tampered, changed_blob):
        with BlobClient.from_blob_url(url, api_version=STORAGE_API_VERSION) as reader:
            with pytest.raises(HttpResponseError) as refused:
                reader.download_blob()
            assert refused.value.status_code == 403


def test_same_five_minute_link_stops_working_after_its_deadline(
    live_store: BlobPhotoStore,
) -> None:
    """Wait for the real provider deadline; a mocked Python clock cannot prove it."""
    reference = live_store.put_image(synthetic_photo(), max_dimension=1280)
    link = live_store.read_link(reference)
    with (
        BlobClient.from_blob_url(link.url, api_version=STORAGE_API_VERSION) as reader,
        Image.open(BytesIO(reader.download_blob().readall())) as image,
    ):
        assert image.size == (1280, 640)
    # This acceptance test deliberately takes five minutes. Wait on a timer
    # event rather than sleeping in application code or altering server time.
    delay = max(0, (link.expires_at - datetime.now(UTC)).total_seconds()) + 1
    expired = Event()
    timer = Timer(delay, expired.set)
    try:
        timer.start()
        assert expired.wait(timeout=delay + 10), "Expiry timer did not fire"
    finally:
        timer.cancel()
    with BlobClient.from_blob_url(link.url, api_version=STORAGE_API_VERSION) as reader:
        with pytest.raises(HttpResponseError) as refused:
            reader.download_blob()
        assert refused.value.status_code == 403
