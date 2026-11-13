# AI contribution: 50% or more AI-generated
"""Shared data for the GET /api/listings/ tests (US-36): the clock and listings."""

from datetime import UTC, datetime, timedelta
from typing import Any

from modules.households.tests.factories import HouseholdFactory
from modules.listings.tests.factories import ListingFactory

NOW = datetime(2026, 11, 6, 15, tzinfo=UTC)  # 10:00 in Montreal
URL = "/api/listings/"  # the path in docs/03-design/api.md


def _household(holder: Any, **kwargs: Any) -> Any:
    """An online file held by ``holder``, approved and valid unless overridden."""
    values: dict[str, Any] = {
        "channel": "online",
        "holder": holder,
        "created_by": None,
        "status": "approved",
        "approved_at": NOW - timedelta(days=30),
        "expires_at": NOW + timedelta(days=335),
    }
    return HouseholdFactory(**(values | kwargs))


def _listing(start: datetime = NOW + timedelta(hours=1), **kwargs: Any) -> Any:
    """A published listing with a two-hour pickup from ``start``, unless overridden."""
    end = kwargs.pop("pickup_end", start + timedelta(hours=2))
    return ListingFactory(pickup_start=start, pickup_end=end, **kwargs)


def _ids_of(page: dict[str, Any]) -> list[str]:
    """Listing IDs in a decoded page, in order."""
    return [card["id"] for card in page["results"]]
