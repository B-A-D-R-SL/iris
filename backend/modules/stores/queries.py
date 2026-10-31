# AI contribution: 50% or more AI-generated
"""Public read access; consumers never query Store's manager directly."""

from typing import Any
from uuid import UUID

from modules.stores.models import Store


def for_listing_post(store_id: UUID) -> Store | None:
    """Read and lock the store inside the caller's posting transaction."""
    return Store.objects.select_for_update().filter(pk=store_id).first()


def address(store_id: UUID) -> dict[str, Any] | None:
    """Listing locations always come from the offering store's address."""
    result = (
        Store.objects.filter(pk=store_id)
        .values("street_number", "street_name", "unit", "city", "postal_code")
        .first()
    )
    return dict(result) if result is not None else None
