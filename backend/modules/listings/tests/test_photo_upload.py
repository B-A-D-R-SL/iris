# AI contribution: 50% or more AI-generated
"""FIX-02: actual upload boundary, processing, storage failures and rollback."""

import json
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import AzureError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from adapters.blob_photos import BlobPhotoConfig, BlobPhotoStore
from adapters.photo_types import PhotoStorageError
from iris.observability import JsonLogFormatter
from modules.listings import services
from modules.listings.models import Listing
from modules.listings.tests.fake_photo_store import MemoryPhotoStore


def upload() -> SimpleUploadedFile:
    with Image.new("RGB", (2000, 1000), "red") as image:
        exif = Image.Exif()
        exif[271] = "IRIS SYNTHETIC CAMERA"
        output = BytesIO()
        image.save(output, format="PNG", exif=exif)
    return SimpleUploadedFile(
        "synthetic.png", output.getvalue(), content_type="image/png"
    )


def payload(case: SimpleNamespace, photo: SimpleUploadedFile) -> dict[str, Any]:
    return {
        "title": case.data.title,
        "category": case.category.code,
        "quantity": case.data.quantity,
        "pickup_start": case.data.pickup_start.isoformat(),
        "pickup_end": case.data.pickup_end.isoformat(),
        "best_before": case.data.best_before.isoformat(),
        "safe_and_allowed": True,
        "photo": photo,
    }


@pytest.fixture
def memory_store(monkeypatch: pytest.MonkeyPatch) -> MemoryPhotoStore:
    store = MemoryPhotoStore()
    monkeypatch.setattr(services, "_photo_store", lambda: store)
    return store


def test_api_saves_reference_and_processed_image(
    posting_case: SimpleNamespace,
    memory_store: MemoryPhotoStore,
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
    photo = memory_store.photos[listing.photo_ref]
    assert (photo.width, photo.height) == (1280, 640)
    with Image.open(BytesIO(photo.content)) as image:
        assert not image.getexif()
    assert "photo_ref" not in response.json()


def test_api_rejects_corrupt_image_without_saving_or_uploading(
    posting_case: SimpleNamespace,
    memory_store: MemoryPhotoStore,
) -> None:
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_authenticate(user=posting_case.user)
    photo = SimpleUploadedFile(
        "bad.jpg", b"\xff\xd8\xffinvalid", content_type="image/jpeg"
    )
    response = client.post(
        reverse("store-listing-create"),
        payload(posting_case, photo),
        format="multipart",
    )
    assert response.status_code == 400
    assert "photo" in response.json()["fields"]
    assert not Listing.objects.exists()
    assert memory_store.photos == {}


@pytest.mark.parametrize(
    ("language", "message"),
    [
        ("en", "Posting is temporarily unavailable."),
        ("fr", "La publication est temporairement indisponible."),
    ],
)
def test_api_storage_failure_returns_generic_503_and_safe_event(
    posting_case: SimpleNamespace,
    memory_store: MemoryPhotoStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    language: str,
    message: str,
) -> None:
    def unavailable(*args: Any, **kwargs: Any) -> str:
        raise PhotoStorageError("sensitive storage credentials")

    monkeypatch.setattr(memory_store, "put_image", unavailable)
    client = APIClient(HTTP_ACCEPT_LANGUAGE=language)
    client.force_authenticate(user=posting_case.user)
    response = client.post(
        reverse("store-listing-create"),
        payload(posting_case, upload()),
        format="multipart",
    )
    assert response.status_code == 503
    assert response.json()["message"] == message
    assert not Listing.objects.exists()
    assert "sensitive" not in caplog.text
    assert "listing_photo_store_failed" in caplog.text


def test_database_failure_cleans_the_processed_photo(
    posting_case: SimpleNamespace,
    memory_store: MemoryPhotoStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_save(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(Listing, "save", fail_save)
    photo = upload()
    with pytest.raises(RuntimeError, match="simulated database failure"):
        services.post_listing(
            posting_case.store.pk, posting_case.user, posting_case.data, photo=photo
        )
    assert not Listing.objects.exists()
    assert memory_store.photos == {}


def test_invalid_photo_factory_signature_returns_generic_posting_error(
    posting_case: SimpleNamespace, settings: Any
) -> None:
    """Pointing configuration at the adapter class cannot leak a constructor error."""
    settings.LISTING_PHOTO_STORE_BACKEND = "adapters.blob_photos.BlobPhotoStore"
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_authenticate(user=posting_case.user)
    response = client.post(
        reverse("store-listing-create"),
        payload(posting_case, upload()),
        format="multipart",
    )
    assert response.status_code == 503
    assert response.json()["message"] == "Posting is temporarily unavailable."
    assert not Listing.objects.exists()


def test_upload_and_cleanup_failure_logs_the_orphan_in_json(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A reference survives JSON formatting even when upload never returns it."""
    config = BlobPhotoConfig(
        container="iris-unit-tests",
        account_name="unitaccount",
        account_key="c3ludGhldGljLWtleQ==",
        account_url="https://unitaccount.blob.core.windows.net",
    )
    client = MagicMock()
    client.__enter__.return_value = client
    container = client.get_container_client.return_value
    container.get_container_access_policy.return_value = {"public_access": None}
    blob = container.get_blob_client.return_value
    blob.upload_blob.side_effect = AzureError("sensitive upload details")
    blob.delete_blob.side_effect = AzureError("sensitive cleanup details")
    storage = BlobPhotoStore(config, client_factory=lambda *args, **kwargs: client)
    content = upload().read()
    with pytest.raises(PhotoStorageError):
        storage.put_image(content, max_dimension=1280)
    reference = container.get_blob_client.call_args.args[0]
    records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "listing_photo_cleanup_failed"
    ]
    assert len(records) == 1
    encoded = JsonLogFormatter().format(records[0])
    assert json.loads(encoded)["photo_ref"] == reference
    assert "sensitive" not in encoded


def test_failed_rollback_cleanup_identifies_the_orphan_without_masking_database_error(
    posting_case: SimpleNamespace,
    memory_store: MemoryPhotoStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Operators get only the opaque orphan reference; the original error survives."""

    def fail_save(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("simulated database failure")

    def fail_delete(reference: str) -> None:
        raise PhotoStorageError("sensitive provider details")

    monkeypatch.setattr(Listing, "save", fail_save)
    monkeypatch.setattr(memory_store, "delete", fail_delete)
    photo = upload()
    with pytest.raises(RuntimeError, match="simulated database failure"):
        services.post_listing(
            posting_case.store.pk, posting_case.user, posting_case.data, photo=photo
        )
    assert not Listing.objects.exists()
    assert len(memory_store.photos) == 1
    records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "listing_photo_cleanup_failed"
    ]
    assert len(records) == 1
    assert getattr(records[0], "photo_ref", None) == next(iter(memory_store.photos))
    encoded = JsonLogFormatter().format(records[0])
    assert json.loads(encoded)["photo_ref"] == next(iter(memory_store.photos))
    assert "sensitive provider details" not in encoded
    assert "sensitive provider details" not in caplog.text
