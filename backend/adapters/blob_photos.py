# AI contribution: 50% or more AI-generated
"""Private listing photos in Azure Blob Storage (Azurite in development)."""

import base64
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlsplit
from uuid import uuid4

from azure.core.credentials import AzureNamedKeyCredential
from azure.core.exceptions import AzureError, ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContainerClient,
    ContentSettings,
    LinearRetry,
    generate_blob_sas,
)

from adapters.photo_types import PhotoReadLink, PhotoStorageError
from adapters.photos import DEFAULT_MAX_BYTES, DEFAULT_MAX_PIXELS, process_photo

logger = logging.getLogger("iris.listings")
LINK_LIFETIME = timedelta(minutes=5)
# Use an API supported by both Azure and the pinned Azurite emulator, independent
# of the SDK's evolving default. This does not disable server version checks.
STORAGE_API_VERSION = "2023-11-03"
REFERENCE = re.compile(r"listing-photos/[0-9a-f]{32}\.(?:jpg|png)\Z")
LOCAL_HOSTS = frozenset({"azurite", "localhost", "127.0.0.1", "::1"})


def _endpoint(value: str, allow_http: bool) -> str:
    """Reject credential-bearing URLs and HTTP outside explicit local development."""
    parsed = urlsplit(value)
    local_http = allow_http and parsed.hostname in LOCAL_HOSTS
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or (parsed.scheme != "https" and not (parsed.scheme == "http" and local_http))
    ):
        raise PhotoStorageError("Invalid photo storage endpoint.")
    return value.rstrip("/")


@dataclass(frozen=True)
class BlobPhotoConfig:
    """Validated account and endpoint settings with credentials hidden from repr."""

    container: str
    account_name: str
    account_key: str = field(repr=False)
    account_url: str
    public_endpoint: str = ""
    allow_http: bool = False
    max_pixels: int = DEFAULT_MAX_PIXELS

    def __post_init__(self) -> None:
        """Reject invalid names, keys, limits and endpoints before contacting storage."""
        if not re.fullmatch(r"[a-z0-9]{3,24}", self.account_name):
            raise PhotoStorageError("Photo storage account is not configured.")
        if not re.fullmatch(
            r"[a-z0-9](?:[a-z0-9]|-(?!-)){1,61}[a-z0-9]", self.container
        ):
            raise PhotoStorageError("Photo storage container is not configured.")
        try:
            if not base64.b64decode(self.account_key, validate=True):
                raise ValueError("empty key")
        except ValueError:
            raise PhotoStorageError(
                "Photo storage credentials are not configured."
            ) from None
        if type(self.max_pixels) is not int or self.max_pixels <= 0:
            raise PhotoStorageError("Invalid photo processing limit.")
        _endpoint(self.account_url, self.allow_http)
        _endpoint(self.public_endpoint or self.account_url, self.allow_http)


def config_from_connection_string(
    connection_string: str,
    *,
    container: str,
    public_endpoint: str = "",
    allow_http: bool = False,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> BlobPhotoConfig:
    """Parse an account-key connection string without exposing its contents on failure."""
    try:
        entries = (item.split("=", 1) for item in connection_string.split(";") if item)
        parts = {key: value for key, value in entries}
        account_name = parts["AccountName"]
        endpoint = parts.get("BlobEndpoint") or (
            f"{parts.get('DefaultEndpointsProtocol', 'https')}://{account_name}"
            f".blob.{parts.get('EndpointSuffix', 'core.windows.net')}"
        )
        return BlobPhotoConfig(
            container,
            account_name,
            parts["AccountKey"],
            endpoint,
            public_endpoint,
            allow_http,
            max_pixels,
        )
    except (KeyError, ValueError):
        raise PhotoStorageError(
            "Photo storage credentials are not configured."
        ) from None


class BlobPhotoStore:
    """Process uploads and manage private blobs through short-lived SDK clients."""

    def __init__(
        self,
        config: BlobPhotoConfig,
        *,
        client_factory: Callable[..., BlobServiceClient] = BlobServiceClient,
    ) -> None:
        """Accept validated configuration and an injectable SDK factory for tests."""
        self.config = config
        self._client_factory = client_factory

    def _client(self) -> BlobServiceClient:
        """Build a key-authenticated client with bounded retries and timeouts."""
        return self._client_factory(
            self.config.account_url,
            credential=AzureNamedKeyCredential(
                self.config.account_name, self.config.account_key
            ),
            api_version=STORAGE_API_VERSION,
            # Avoid the SDK's 15-21 second default backoff on request paths.
            retry_policy=LinearRetry(backoff=1, retry_total=1, random_jitter_range=0),
            connection_timeout=3,
            read_timeout=5,
            logging_enable=False,
        )

    def _container(
        self, service: BlobServiceClient, *, create: bool = False
    ) -> ContainerClient:
        """Optionally create the container, then verify even existing ones are private."""
        container = service.get_container_client(self.config.container)
        if create:
            try:
                container.create_container(public_access=None)
            except ResourceExistsError:
                logger.info(
                    "listing_photo_container_reused",
                    extra={"event": "listing_photo_container_reused"},
                )
        if container.get_container_access_policy().get("public_access") is not None:
            raise PhotoStorageError("Photo storage container must be private.")
        return container

    def put_image(
        self,
        content: bytes,
        *,
        max_dimension: int,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> str:
        """Upload cleaned image bytes under a new reference; clean up uncertain writes."""
        photo = process_photo(
            content,
            max_dimension=max_dimension,
            max_bytes=max_bytes,
            max_pixels=self.config.max_pixels,
        )
        extension = "jpg" if photo.content_type == "image/jpeg" else "png"
        reference = f"listing-photos/{uuid4().hex}.{extension}"
        try:
            with self._client() as service:
                blob = self._container(service, create=True).get_blob_client(reference)
                try:
                    blob.upload_blob(
                        photo.content,
                        overwrite=False,
                        content_settings=ContentSettings(
                            content_type=photo.content_type,
                            cache_control="private, no-store",
                        ),
                        max_concurrency=1,
                    )
                except ResourceExistsError:
                    # Never delete an existing object on a name collision.
                    raise
                except AzureError:
                    self._cleanup(blob.delete_blob, reference=reference)
                    raise
        except AzureError:
            raise PhotoStorageError(
                "Photo upload is temporarily unavailable."
            ) from None
        logger.info("listing_photo_stored", extra={"event": "listing_photo_stored"})
        return reference

    @staticmethod
    def _cleanup(delete: Callable[..., object], *, reference: str) -> None:
        """Attempt compensating deletion without masking the original upload failure."""
        try:
            delete(delete_snapshots="include")
        except ResourceNotFoundError:
            logger.info(
                "listing_photo_cleanup_not_found",
                extra={"event": "listing_photo_cleanup_not_found"},
            )
            return
        except AzureError:
            logger.error(
                "listing_photo_cleanup_failed",
                extra={"event": "listing_photo_cleanup_failed", "photo_ref": reference},
            )
        else:
            logger.info(
                "listing_photo_cleanup_completed",
                extra={"event": "listing_photo_cleanup_completed"},
            )

    @staticmethod
    def _reference(reference: str) -> None:
        """Accept only server-generated listing photo references, never arbitrary paths."""
        if not REFERENCE.fullmatch(reference):
            raise PhotoStorageError("Invalid photo reference.")

    def delete(self, reference: str) -> None:
        """Delete a photo idempotently and return a generic error for storage failures."""
        self._reference(reference)
        try:
            with self._client() as service:
                service.get_blob_client(self.config.container, reference).delete_blob(
                    delete_snapshots="include",
                )
        except ResourceNotFoundError:
            logger.info(
                "listing_photo_delete_not_found",
                extra={"event": "listing_photo_delete_not_found"},
            )
            return
        except AzureError:
            raise PhotoStorageError(
                "Photo deletion is temporarily unavailable."
            ) from None
        logger.info("listing_photo_deleted", extra={"event": "listing_photo_deleted"})

    def read_link(self, reference: str, *, at: datetime | None = None) -> PhotoReadLink:
        """Issue one scoped read link after checking the container's privacy."""
        return self.read_links([reference], at=at)[reference]

    def read_links(
        self, references: list[str], *, at: datetime | None = None
    ) -> dict[str, PhotoReadLink]:
        """Check container privacy once for this batch; never cache it across requests."""
        references = list(dict.fromkeys(references))
        for reference in references:
            self._reference(reference)
        if not references:
            return {}
        issued = at or datetime.now(UTC)
        if issued.utcoffset() is None:
            raise ValueError("A timezone-aware timestamp is required.")
        expires = issued.astimezone(UTC).replace(microsecond=0) + LINK_LIFETIME
        endpoint = self.config.public_endpoint or self.config.account_url
        try:
            with self._client() as service:
                self._container(service)
            return {
                reference: self._sign_link(reference, endpoint, expires)
                for reference in references
            }
        except (AzureError, ValueError):
            raise PhotoStorageError(
                "Photo access is temporarily unavailable."
            ) from None

    def _sign_link(
        self, reference: str, endpoint: str, expires: datetime
    ) -> PhotoReadLink:
        """Sign one validated blob reference with read-only access and a fixed expiry."""
        token = generate_blob_sas(
            account_name=self.config.account_name,
            container_name=self.config.container,
            blob_name=reference,
            account_key=self.config.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expires,
            protocol="https,http" if urlsplit(endpoint).scheme == "http" else "https",
            cache_control="private, no-store",
        )
        url = f"{endpoint.rstrip('/')}/{self.config.container}/{quote(reference, safe='/')}?{token}"
        return PhotoReadLink(url, expires)
