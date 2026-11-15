# AI contribution: 50% or more AI-generated
"""cancel_all_for_store and the store admin listing queries (US-14)."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from django.db import transaction

from modules.listings import queries
from modules.listings.models import Listing, ListingStatus
from modules.listings.services import cancel_all_for_store
from modules.listings.tests.factories import ListingFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 14, 15, tzinfo=UTC)


def _store() -> Any:
    return StoreFactory()


def _listing(store: Any, *, starts_in: timedelta, **kwargs: Any) -> Listing:
    start = NOW + starts_in
    values = {
        "store": store,
        "pickup_start": start,
        "pickup_end": start + timedelta(hours=2),
    }
    return cast(Listing, ListingFactory(**(values | kwargs)))


def _cancel(store_id: Any, now: datetime = NOW) -> list[Any]:
    with transaction.atomic():
        return cancel_all_for_store(store_id, now=now)


# rule: BR-STORE-002
def test_cancels_published_listings_whose_pickup_has_not_ended() -> None:
    store = _store()
    upcoming = _listing(store, starts_in=timedelta(hours=3), quantity_reserved=2)
    in_progress = _listing(store, starts_in=timedelta(hours=-1))

    cancelled = _cancel(store.pk)

    assert sorted(cancelled) == sorted([upcoming.pk, in_progress.pk])
    for listing in (upcoming, in_progress):
        listing.refresh_from_db()
        assert listing.status == ListingStatus.CANCELLED
        assert listing.cancelled_at == NOW
    upcoming.refresh_from_db()
    assert upcoming.quantity_reserved == 2  # kept as history


# rule: BR-STORE-002
def test_leaves_ended_closed_and_other_stores_listings_alone() -> None:
    store = _store()
    ended = _listing(store, starts_in=timedelta(hours=-5))
    closed = _listing(store, starts_in=timedelta(hours=3), status=ListingStatus.CLOSED)
    other_store = _listing(_store(), starts_in=timedelta(hours=3))

    assert _cancel(store.pk) == []

    for listing in (ended, closed, other_store):
        before = listing.status
        listing.refresh_from_db()
        assert listing.status == before
        assert listing.cancelled_at is None


def test_ending_exactly_now_is_not_cancelled() -> None:
    store = _store()
    _listing(store, starts_in=timedelta(hours=-2))  # pickup_end == NOW

    assert _cancel(store.pk) == []


@pytest.mark.django_db(transaction=True)
def test_requires_a_transaction() -> None:
    with pytest.raises(RuntimeError):
        cancel_all_for_store(_store().pk, now=NOW)


def test_requires_an_aware_clock() -> None:
    with pytest.raises(ValueError), transaction.atomic():
        cancel_all_for_store(_store().pk, now=NOW.replace(tzinfo=None))


def test_open_listing_queries_count_only_what_deactivation_cancels() -> None:
    store, quiet = _store(), _store()
    first = _listing(store, starts_in=timedelta(hours=3))
    second = _listing(store, starts_in=timedelta(hours=-1))
    _listing(store, starts_in=timedelta(hours=-5))
    _listing(store, starts_in=timedelta(hours=3), status=ListingStatus.CANCELLED)

    assert queries.open_listing_counts([store.pk, quiet.pk], NOW) == {store.pk: 2}
    assert sorted(queries.open_listing_ids(store.pk, NOW)) == sorted(
        [first.pk, second.pk]
    )


def test_cancellation_details_gives_the_titles() -> None:
    listing = _listing(_store(), starts_in=timedelta(hours=3), title="Pain")

    assert queries.cancellation_details([listing.pk]) == {listing.pk: "Pain"}
