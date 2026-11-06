# AI contribution: 50% or more AI-generated
"""US-36: which listings a household sees, and the browse filters and order.

BR-LIST-004: a household sees a listing when it is published, has units left
and its pickup has not ended. BR-LIST-005: "pickup today" keeps listings that
can still be picked up before midnight, Montreal time.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from modules.categories.models import Category
from modules.categories.tests.factories import CategoryFactory
from modules.listings.models import Listing, ListingStatus
from modules.listings.queries import browse_listings, visible_listings
from modules.listings.tests.factories import ListingFactory
from modules.stores.models import Store
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 6, 15, tzinfo=UTC)  # 10:00 in Montreal
TONIGHT = datetime(2026, 11, 7, 5, tzinfo=UTC)  # midnight in Montreal
HOUSEHOLD = uuid4()


def _listing(start: datetime = NOW + timedelta(hours=1), **kwargs: Any) -> Listing:
    end = kwargs.pop("pickup_end", start + timedelta(hours=2))
    return cast(Listing, ListingFactory(pickup_start=start, pickup_end=end, **kwargs))


def _visible(household: UUID | None = HOUSEHOLD) -> set[UUID]:
    return set(visible_listings(household, NOW).values_list("id", flat=True))


def _browsed(**filters: Any) -> list[UUID]:
    return [card["id"] for card in browse_listings(HOUSEHOLD, NOW, **filters)]


class TestVisibility:
    """BR-LIST-004."""

    def test_a_published_listing_with_units_left_and_a_future_end_is_visible(
        self,
    ) -> None:
        listing = _listing()
        assert _visible() == {listing.id}

    @pytest.mark.parametrize("status", [ListingStatus.CLOSED, ListingStatus.CANCELLED])
    def test_a_listing_that_is_not_published_is_hidden(self, status: str) -> None:
        _listing(status=status)
        assert _visible() == set()

    def test_a_listing_with_every_unit_reserved_is_hidden(self) -> None:
        _listing(quantity_total=3, quantity_reserved=3)
        assert _visible() == set()

    def test_a_listing_with_one_unit_left_is_visible(self) -> None:
        listing = _listing(quantity_total=3, quantity_reserved=2)
        assert _visible() == {listing.id}

    def test_a_pickup_ending_exactly_now_is_hidden(self) -> None:
        _listing(start=NOW - timedelta(hours=2), pickup_end=NOW)
        assert _visible() == set()

    def test_a_pickup_ending_one_second_from_now_is_visible(self) -> None:
        listing = _listing(
            start=NOW - timedelta(hours=2), pickup_end=NOW + timedelta(seconds=1)
        )
        assert _visible() == {listing.id}

    def test_a_pickup_already_in_progress_is_visible(self) -> None:
        listing = _listing(start=NOW - timedelta(minutes=30))
        assert _visible() == {listing.id}

    def test_without_an_approved_household_nothing_is_visible(self) -> None:
        _listing()
        assert _visible(household=None) == set()

    def test_until_tiers_exist_every_approved_household_sees_every_listing(
        self,
    ) -> None:
        listings = {_listing().id, _listing().id}
        assert _visible(uuid4()) == _visible(uuid4()) == listings

    def test_a_naive_clock_is_refused(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            visible_listings(HOUSEHOLD, datetime(2026, 11, 6, 10))  # noqa: DTZ001


class TestBrowseFilters:
    def test_category_filter_keeps_only_that_category_code(self) -> None:
        bakery = cast(Category, CategoryFactory(code="bakery"))
        wanted = _listing(category=bakery)
        _listing()
        assert _browsed(category="bakery") == [wanted.id]

    def test_an_unknown_category_code_matches_nothing(self) -> None:
        _listing()
        assert _browsed(category="no_such_category") == []

    def test_store_filter_keeps_only_that_store(self) -> None:
        store = cast(Store, StoreFactory())
        wanted = _listing(store=store)
        _listing()
        assert _browsed(store=store.pk) == [wanted.id]

    def test_an_unknown_store_matches_nothing(self) -> None:
        _listing()
        assert _browsed(store=uuid4()) == []

    def test_pickup_today_keeps_windows_open_before_montreal_midnight(self) -> None:
        """BR-LIST-005."""
        started_last_night = _listing(
            start=NOW - timedelta(hours=11), pickup_end=NOW + timedelta(hours=1)
        )
        later_today = _listing(start=NOW + timedelta(hours=3))
        last_minute = _listing(start=TONIGHT - timedelta(minutes=1))
        _listing(start=TONIGHT)  # starts at midnight: tomorrow
        _listing(start=NOW + timedelta(days=1))
        assert _browsed(pickup_today=True) == [
            started_last_night.id,
            later_today.id,
            last_minute.id,
        ]

    def test_without_the_today_filter_later_days_are_listed_too(self) -> None:
        today = _listing()
        tomorrow = _listing(start=NOW + timedelta(days=1))
        assert _browsed() == [today.id, tomorrow.id]

    def test_filters_combine(self) -> None:
        store = cast(Store, StoreFactory())
        bakery = cast(Category, CategoryFactory(code="bakery"))
        wanted = _listing(store=store, category=bakery)
        _listing(store=store)
        _listing(category=bakery)
        _listing(store=store, category=bakery, start=NOW + timedelta(days=1))
        assert _browsed(category="bakery", store=store.pk, pickup_today=True) == [
            wanted.id
        ]

    def test_filters_never_show_a_hidden_listing(self) -> None:
        store = cast(Store, StoreFactory())
        _listing(store=store, status=ListingStatus.CANCELLED)
        assert _browsed(store=store.pk, pickup_today=True) == []


class TestBrowseCards:
    def test_cards_are_sorted_by_pickup_start(self) -> None:
        third = _listing(start=NOW + timedelta(hours=5))
        first = _listing(start=NOW + timedelta(hours=1))
        second = _listing(start=NOW + timedelta(hours=3))
        assert _browsed() == [first.id, second.id, third.id]

    def test_listings_starting_together_keep_a_stable_order_by_id(self) -> None:
        same_start = [_listing(start=NOW + timedelta(hours=2)) for _ in range(3)]
        assert _browsed() == sorted(listing.id for listing in same_start)

    def test_a_card_has_the_store_window_units_left_and_best_before(self) -> None:
        store = cast(Store, StoreFactory(unit="2"))
        listing = _listing(store=store, quantity_total=10, quantity_reserved=3)
        assert list(browse_listings(HOUSEHOLD, NOW)) == [
            {
                "id": listing.id,
                "title": listing.title,
                "unit": "item",
                "pickup_start": NOW + timedelta(hours=1),
                "pickup_end": NOW + timedelta(hours=3),
                "best_before": listing.best_before,
                "store_id": store.pk,
                "units_left": 7,
                "category_code": listing.category.code,
                "store_name": store.name,
                "store_street_number": store.street_number,
                "store_street_name": store.street_name,
                "store_unit": "2",
                "store_city": store.city,
                "store_postal_code": store.postal_code,
            }
        ]

    def test_a_page_of_cards_from_many_stores_takes_one_query(
        self, django_assert_num_queries: Any
    ) -> None:
        for _ in range(3):
            _listing()
        with django_assert_num_queries(1):
            cards = list(browse_listings(HOUSEHOLD, NOW)[:20])
        assert len({card["store_id"] for card in cards}) == 3
