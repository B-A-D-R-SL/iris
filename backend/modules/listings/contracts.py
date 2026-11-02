# AI contribution: 50% or more AI-generated
"""Small contracts for pending safety and photo integrations; no test defaults."""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol

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

    def put_image(self, content: bytes, *, max_dimension: int) -> str: ...

    def delete(self, reference: str) -> None: ...
