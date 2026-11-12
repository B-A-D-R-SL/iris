# AI contribution: 50% or more AI-generated
"""Private storage contract against an in-memory SDK stand-in; no network."""

import base64
import logging
from datetime import UTC, datetime, timedelta
from functools import partial
from io import BytesIO
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest
from azure.core.exceptions import (
    AzureError,
    ResourceExistsError,
    ResourceNotFoundError,
    ServiceRequestError,
)
from azure.core.pipeline.transport import HttpTransport, RequestsTransport
from azure.storage.blob import BlobServiceClient
from PIL import Image

from adapters.blob_photos import (
    BlobPhotoConfig,
    BlobPhotoStore,
    config_from_connection_string,
)
from adapters.photo_types import PhotoStorageError
from adapters.photos import PhotoValidationError

REFERENCE = "listing-photos/" + "a" * 32 + ".png"
NOW = datetime(2026, 11, 10, 15, tzinfo=UTC)


def photo_config(**overrides: object) -> BlobPhotoConfig:
    values = {
        "container": "iris-unit-tests",
        "account_name": "unitaccount",
        "account_key": base64.b64encode(b"synthetic-unit-test-key").decode(),
        "account_url": "https://unitaccount.blob.core.windows.net",
    }
    return BlobPhotoConfig(**(values | overrides))  # type: ignore[arg-type]


def fake_sdk(config: BlobPhotoConfig | None = None) -> tuple[BlobPhotoStore, MagicMock]:
    client = MagicMock(spec=BlobServiceClient)
    client.__enter__.return_value = client
    container = client.get_container_client.return_value
    container.get_container_access_policy.return_value = {"public_access": None}
    client.get_blob_client.return_value = container.get_blob_client.return_value
    return BlobPhotoStore(
        config or photo_config(), client_factory=MagicMock(return_value=client)
    ), client


def photo_bytes() -> bytes:
    with Image.new("RGB", (2000, 1000), "red") as image:
        exif = Image.Exif()
        exif[271] = "IRIS SYNTHETIC CAMERA"
        output = BytesIO()
        image.save(output, format="PNG", exif=exif)
        return output.getvalue()


def test_storage_connection_failure_retries_once_after_one_second(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the real SDK policy without networking or a wall-clock delay."""
    send = MagicMock(side_effect=ServiceRequestError("synthetic connection failure"))
    sleep = MagicMock()
    monkeypatch.setattr(RequestsTransport, "send", send)
    monkeypatch.setattr(HttpTransport, "sleep", sleep)
    store = BlobPhotoStore(photo_config())
    with pytest.raises(PhotoStorageError, match="temporarily unavailable"):
        store.read_link(REFERENCE)
    assert send.call_count == 2
    sleep.assert_called_once_with(1)


def test_upload_stores_only_processed_bytes_and_never_overwrites() -> None:
    store, client = fake_sdk()
    reference = store.put_image(photo_bytes(), max_dimension=1280)
    container = client.get_container_client.return_value
    container.create_container.assert_called_once_with(public_access=None)
    blob = container.get_blob_client.return_value
    args, kwargs = blob.upload_blob.call_args
    assert kwargs["overwrite"] is False
    assert kwargs["content_settings"].content_type == "image/png"
    assert kwargs["content_settings"].cache_control == "private, no-store"
    with Image.open(BytesIO(args[0])) as image:
        image.load()
        assert image.size == (1280, 640)
        assert not image.getexif()
    assert reference.startswith("listing-photos/")
    assert reference.endswith(".png")
    client.__exit__.assert_called_once()


@pytest.mark.parametrize("operation", ["put", "read"])
def test_public_containers_are_refused_before_upload_or_link_creation(
    operation: str,
) -> None:
    store, client = fake_sdk()
    container = client.get_container_client.return_value
    container.get_container_access_policy.return_value = {"public_access": "blob"}
    action = (
        partial(store.put_image, photo_bytes(), max_dimension=1280)
        if operation == "put"
        else partial(store.read_link, REFERENCE, at=NOW)
    )
    with pytest.raises(PhotoStorageError, match="private"):
        action()
    container.get_blob_client.return_value.upload_blob.assert_not_called()


def test_existing_private_container_is_reused(caplog: pytest.LogCaptureFixture) -> None:
    """Container reuse still checks privacy and logs no provider exception text."""
    caplog.set_level(logging.INFO, logger="iris.listings")
    store, client = fake_sdk()
    client.get_container_client.return_value.create_container.side_effect = (
        ResourceExistsError("sensitive provider details")
    )
    store.put_image(photo_bytes(), max_dimension=1280)
    client.get_container_client.return_value.get_container_access_policy.assert_called_once()
    assert "listing_photo_container_reused" in [
        getattr(record, "event", None) for record in caplog.records
    ]
    assert "sensitive provider details" not in caplog.text


def test_invalid_photo_never_contacts_storage() -> None:
    store, client = fake_sdk()
    with pytest.raises(PhotoValidationError):
        store.put_image(b"\xff\xd8\xffinvalid", max_dimension=1280)
    client.get_container_client.assert_not_called()


def test_upload_failure_cleans_its_object_and_hides_provider_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An uncertain write is removed and its cleanup event contains no provider data."""
    caplog.set_level(logging.INFO, logger="iris.listings")
    store, client = fake_sdk()
    blob = client.get_container_client.return_value.get_blob_client.return_value
    blob.upload_blob.side_effect = AzureError("sensitive provider error")
    content = photo_bytes()
    with pytest.raises(PhotoStorageError) as caught:
        store.put_image(content, max_dimension=1280)
    assert "sensitive" not in str(caught.value)
    blob.delete_blob.assert_called_once_with(delete_snapshots="include")
    assert [getattr(record, "event", None) for record in caplog.records] == [
        "listing_photo_cleanup_completed"
    ]
    assert "sensitive provider error" not in caplog.text


@pytest.mark.parametrize("operation", ["cleanup", "delete"])
def test_missing_blob_is_harmless_and_logs_only_a_safe_event(
    operation: str, caplog: pytest.LogCaptureFixture
) -> None:
    """A missing blob stays idempotent while every handled failure has a safe event."""
    caplog.set_level(logging.INFO, logger="iris.listings")
    store, client = fake_sdk()
    blob = client.get_blob_client.return_value
    blob.delete_blob.side_effect = ResourceNotFoundError(
        "sensitive missing blob details"
    )
    if operation == "cleanup":
        blob.upload_blob.side_effect = AzureError("sensitive upload details")
        content = photo_bytes()
        with pytest.raises(PhotoStorageError):
            store.put_image(content, max_dimension=1280)
    else:
        store.delete(REFERENCE)
    assert [getattr(record, "event", None) for record in caplog.records] == [
        f"listing_photo_{operation}_not_found"
    ]
    assert "sensitive" not in caplog.text


def test_name_collision_never_deletes_an_existing_object() -> None:
    store, client = fake_sdk()
    blob = client.get_container_client.return_value.get_blob_client.return_value
    blob.upload_blob.side_effect = ResourceExistsError()
    content = photo_bytes()
    with pytest.raises(PhotoStorageError):
        store.put_image(content, max_dimension=1280)
    blob.delete_blob.assert_not_called()


def test_failed_cleanup_logs_only_a_safe_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store, client = fake_sdk()
    blob = client.get_container_client.return_value.get_blob_client.return_value
    blob.upload_blob.side_effect = AzureError("private upload details")
    blob.delete_blob.side_effect = AzureError("private cleanup details")
    content = photo_bytes()
    with pytest.raises(PhotoStorageError):
        store.put_image(content, max_dimension=1280)
    assert [getattr(record, "event", None) for record in caplog.records] == [
        "listing_photo_cleanup_failed"
    ]
    reference = client.get_container_client.return_value.get_blob_client.call_args.args[
        0
    ]
    assert getattr(caplog.records[0], "photo_ref", None) == reference
    assert "private" not in caplog.text


def test_delete_is_idempotent_and_reports_other_failures() -> None:
    store, client = fake_sdk()
    blob = client.get_blob_client.return_value
    blob.delete_blob.side_effect = ResourceNotFoundError()
    store.delete(REFERENCE)
    blob.delete_blob.side_effect = AzureError("private details")
    with pytest.raises(PhotoStorageError, match="temporarily unavailable"):
        store.delete(REFERENCE)


def test_links_are_read_only_for_one_blob_and_expire_in_five_minutes() -> None:
    store, _ = fake_sdk()
    link = store.read_link(REFERENCE, at=NOW)
    query = parse_qs(urlsplit(link.url).query)
    assert link.expires_at == NOW + timedelta(minutes=5)
    assert query["se"] == ["2026-11-10T15:05:00Z"]
    assert query["sp"] == ["r"]
    assert query["sr"] == ["b"]
    assert query["spr"] == ["https"]
    assert query["rscc"] == ["private, no-store"]
    assert query["sig"]
    assert urlsplit(link.url).path == "/iris-unit-tests/" + REFERENCE
    assert "sig=" not in repr(link)
    assert store.config.account_key not in repr(store.config)


def test_browser_endpoint_replaces_docker_host_without_changing_signed_resource() -> (
    None
):
    config = photo_config(
        account_url="http://azurite:10000/unitaccount",
        allow_http=True,
        public_endpoint="http://localhost:10000/unitaccount",
    )
    store, _ = fake_sdk(config)
    link = store.read_link(REFERENCE, at=NOW)
    assert link.url.startswith("http://localhost:10000/unitaccount/iris-unit-tests/")
    assert "azurite" not in link.url


def test_https_links_stay_https_only_even_when_local_http_is_enabled() -> None:
    store, _ = fake_sdk(photo_config(allow_http=True))
    link = store.read_link(REFERENCE, at=NOW)
    assert parse_qs(urlsplit(link.url).query)["spr"] == ["https"]


def test_batch_checks_privacy_once_and_keeps_each_link_scoped_to_its_blob() -> None:
    store, client = fake_sdk()
    second = "listing-photos/" + "b" * 32 + ".jpg"
    links = store.read_links([REFERENCE, second, REFERENCE], at=NOW)
    container = client.get_container_client.return_value
    container.get_container_access_policy.assert_called_once()
    assert set(links) == {REFERENCE, second}
    for reference, link in links.items():
        assert urlsplit(link.url).path == "/iris-unit-tests/" + reference
        query = parse_qs(urlsplit(link.url).query)
        assert query["sp"] == ["r"]
        assert query["se"] == ["2026-11-10T15:05:00Z"]
    assert (
        parse_qs(urlsplit(links[REFERENCE].url).query)["sig"]
        != parse_qs(urlsplit(links[second].url).query)["sig"]
    )


def test_empty_or_invalid_batch_never_contacts_storage() -> None:
    store, client = fake_sdk()
    assert store.read_links([]) == {}
    references = [REFERENCE, "../other"]
    with pytest.raises(PhotoStorageError, match="Invalid photo reference"):
        store.read_links(references)
    client.__enter__.assert_not_called()


def test_batch_rechecks_container_privacy_on_the_next_request() -> None:
    store, client = fake_sdk()
    store.read_links([REFERENCE], at=NOW)
    container = client.get_container_client.return_value
    container.get_container_access_policy.return_value = {"public_access": "blob"}
    references = [REFERENCE]
    with pytest.raises(PhotoStorageError, match="private"):
        store.read_links(references, at=NOW)
    assert container.get_container_access_policy.call_count == 2


@pytest.mark.parametrize("length", [3, 24, 25, 63])
def test_valid_container_name_lengths_are_accepted(length: int) -> None:
    assert photo_config(container="a" * length).container == "a" * length


@pytest.mark.parametrize(
    "reference", ["../other", "https://elsewhere/photo", "x?sig=secret", ""]
)
def test_untrusted_references_are_refused_without_network_access(
    reference: str,
) -> None:
    store, client = fake_sdk()
    for operation in (store.delete, store.read_link):
        with pytest.raises(PhotoStorageError, match="Invalid photo reference"):
            operation(reference)
    client.get_container_client.assert_not_called()


@pytest.mark.parametrize(
    "overrides",
    [
        {"account_url": "http://public.example.test", "allow_http": True},
        {"public_endpoint": "https://example.test/?sig=secret"},
        {"account_key": "not-base64"},
        {"container": "public--photos"},
        {"account_name": ""},
        {"max_pixels": 0},
    ],
)
def test_invalid_configuration_is_refused(overrides: dict[str, object]) -> None:
    with pytest.raises(PhotoStorageError):
        photo_config(**overrides)


def test_connection_string_is_parsed_without_exposing_credentials() -> None:
    config = photo_config()
    connection = (
        f"DefaultEndpointsProtocol=https;AccountName={config.account_name};"
        f"AccountKey={config.account_key};"
    )
    result = config_from_connection_string(connection, container=config.container)
    assert result == config
    with pytest.raises(PhotoStorageError):
        config_from_connection_string("malformed", container=config.container)
