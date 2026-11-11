# AI contribution: 50% or more AI-generated
"""In-memory photo storage for API/transaction tests, with real processing."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from adapters.photo_types import PhotoReadLink
from adapters.photos import DEFAULT_MAX_BYTES, ProcessedPhoto, process_photo


class MemoryPhotoStore:
    def __init__(self) -> None:
        self.photos: dict[str, ProcessedPhoto] = {}

    def put_image(
        self,
        content: bytes,
        *,
        max_dimension: int,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> str:
        photo = process_photo(content, max_dimension=max_dimension, max_bytes=max_bytes)
        extension = "jpg" if photo.content_type == "image/jpeg" else "png"
        reference = f"listing-photos/{uuid4().hex}.{extension}"
        self.photos[reference] = photo
        return reference

    def delete(self, reference: str) -> None:
        self.photos.pop(reference, None)

    def read_link(self, reference: str) -> PhotoReadLink:
        return PhotoReadLink(
            f"https://photos.example.test/{reference}?synthetic-read-token",
            datetime.now(UTC) + timedelta(minutes=5),
        )

    def read_links(self, references: list[str]) -> dict[str, PhotoReadLink]:
        return {reference: self.read_link(reference) for reference in references}
