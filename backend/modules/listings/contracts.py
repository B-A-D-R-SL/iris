# AI contribution: 50% or more AI-generated
"""Small contracts for pending safety and photo integrations; no test defaults."""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from adapters.photo_types import PhotoReadLink
from adapters.photos import DEFAULT_MAX_BYTES
from modules.listings.domain.posting import Refusal


class SafetyChecker(Protocol):
    def __call__(
        self,
        listing_data: Mapping[str, Any],
        category: Mapping[str, Any],
        rules: Mapping[str, Any],
    ) -> Sequence[Refusal]: ...


class ListingPhotoStore(Protocol):
    """An adapter must verify JPEG/PNG, resize and privately store the image.

    It returns an opaque reference, never a public URL. A failed put_image must
    not leave a partially stored object. Tests inject a fake implementation.
    """

    def put_image(
        self, content: bytes, *, max_dimension: int, max_bytes: int = DEFAULT_MAX_BYTES
    ) -> str:
        """Process and privately store bounded image bytes, returning an opaque reference."""
        ...

    def delete(self, reference: str) -> None:
        """Remove a stored image; a reference that is already absent is harmless."""
        ...

    def read_link(self, reference: str) -> PhotoReadLink:
        """Issue temporary read-only access to one stored photo."""
        ...

    def read_links(self, references: list[str]) -> dict[str, PhotoReadLink]:
        """Issue links for an authorized page while sharing its storage privacy check."""
        ...
