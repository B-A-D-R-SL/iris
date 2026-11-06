# AI contribution: 50% or more AI-generated
"""GET /api/listings/ (US-36): approved households browse, everyone else is refused."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.categories.tests.factories import CategoryFactory
from modules.households.tests.factories import HouseholdFactory
from modules.listings.tests.factories import ListingFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 6, 15, tzinfo=UTC)  # 10:00 in Montreal
URL = "/api/listings/"  # the path in docs/03-design/api.md
NOT_APPROVED_EN = "Only approved households can see listings."
NOT_APPROVED_FR = "Seuls les foyers approuvés peuvent voir les offres."
NOT_APPROVED_STATUSES = [
    "draft",
    "submitted",
    "review_required",
    "awaiting_visit",
    "renewal_needed",
    "suspended",
    "rejected",
]


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timezone, "now", lambda: NOW)


@pytest.fixture
def client() -> APIClient:
    return APIClient(HTTP_ACCEPT_LANGUAGE="en")


def _household(holder: Any, **kwargs: Any) -> Any:
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
    end = kwargs.pop("pickup_end", start + timedelta(hours=2))
    return ListingFactory(pickup_start=start, pickup_end=end, **kwargs)


@pytest.fixture
def approved(client: APIClient) -> APIClient:
    """A client signed in, through a real session, as an approved household."""
    user = UserFactory(role="beneficiary")
    _household(user)
    client.force_login(user)
    return client


def _ids(response: Any) -> list[str]:
    return [card["id"] for card in response.json()["results"]]


class TestApprovedHousehold:
    def test_browses_only_visible_listings_as_cards(self, approved: APIClient) -> None:
        store: Any = StoreFactory(name="Épicerie Exemple")
        category = CategoryFactory(code="bakery")
        listing = _listing(
            store=store, category=category, quantity_total=5, quantity_reserved=2
        )
        _listing(status="cancelled")
        _listing(quantity_total=2, quantity_reserved=2)
        _listing(start=NOW - timedelta(hours=3), pickup_end=NOW)

        response = approved.get(URL)

        assert response.status_code == 200
        assert response.json() == {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": str(listing.id),
                    "title": listing.title,
                    "category": "bakery",
                    "store": {
                        "id": str(store.pk),
                        "name": "Épicerie Exemple",
                        "street_number": store.street_number,
                        "street_name": store.street_name,
                        "unit": None,
                        "city": store.city,
                        "postal_code": store.postal_code,
                    },
                    "pickup_start": "2026-11-06T16:00:00Z",
                    "pickup_end": "2026-11-06T18:00:00Z",
                    "units_left": 3,
                    "unit": "item",
                    "best_before": listing.best_before.isoformat(),
                }
            ],
        }

    def test_cards_come_sorted_by_pickup_start(self, approved: APIClient) -> None:
        later = _listing(start=NOW + timedelta(hours=4))
        sooner = _listing(start=NOW + timedelta(hours=1))
        assert _ids(approved.get(URL)) == [str(sooner.id), str(later.id)]

    def test_an_empty_list_is_still_a_page(self, approved: APIClient) -> None:
        response = approved.get(URL)
        assert response.status_code == 200
        assert response.json() == {
            "count": 0,
            "next": None,
            "previous": None,
            "results": [],
        }

    def test_post_is_not_allowed(self, approved: APIClient) -> None:
        response = approved.post(URL, {})
        assert response.status_code == 405
        assert response.json()["code"] == "method_not_allowed"


class TestRefused:
    def test_signed_out_gets_401(self, client: APIClient) -> None:
        response = client.get(URL)
        assert response.status_code == 401
        assert response.json()["code"] == "not_authenticated"

    @pytest.mark.parametrize(
        "role", ["store_staff", "store_manager", "intake_worker", "admin"]
    )
    def test_other_roles_get_403(self, client: APIClient, role: str) -> None:
        store = StoreFactory() if role.startswith("store_") else None
        client.force_login(UserFactory(role=role, store=store))
        _listing()
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json() == {
            "code": "permission_denied",
            "message": NOT_APPROVED_EN,
            "fields": {},
        }

    def test_an_inactive_beneficiary_gets_403(self, client: APIClient) -> None:
        user = UserFactory(role="beneficiary", is_active=False)
        _household(user)
        client.force_authenticate(user)
        assert client.get(URL).status_code == 403

    @pytest.mark.parametrize("status", NOT_APPROVED_STATUSES)
    def test_a_household_that_is_not_approved_gets_403(
        self, client: APIClient, status: str
    ) -> None:
        user = UserFactory(role="beneficiary")
        _household(user, status=status)
        client.force_login(user)
        _listing()
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json() == {
            "code": "household_not_approved",
            "message": NOT_APPROVED_EN,
            "fields": {},
        }

    def test_an_expired_file_still_marked_approved_gets_403(
        self, client: APIClient
    ) -> None:
        user = UserFactory(role="beneficiary")
        _household(user, expires_at=NOW - timedelta(minutes=1))
        client.force_login(user)
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json()["code"] == "household_not_approved"

    def test_a_beneficiary_without_a_household_gets_403(
        self, client: APIClient
    ) -> None:
        client.force_login(UserFactory(role="beneficiary"))
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json()["code"] == "household_not_approved"

    def test_refusal_comes_before_filter_validation(self, client: APIClient) -> None:
        client.force_login(UserFactory(role="beneficiary"))
        assert client.get(URL, {"store": "not-a-uuid"}).status_code == 403

    def test_the_refusal_is_in_french_by_default(self) -> None:
        client = APIClient()
        client.force_login(UserFactory(role="beneficiary"))
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json()["message"] == NOT_APPROVED_FR


class TestFilters:
    def test_category(self, approved: APIClient) -> None:
        wanted = _listing(category=CategoryFactory(code="bakery"))
        _listing()
        assert _ids(approved.get(URL, {"category": "bakery"})) == [str(wanted.id)]

    def test_store(self, approved: APIClient) -> None:
        store: Any = StoreFactory()
        wanted = _listing(store=store)
        _listing()
        assert _ids(approved.get(URL, {"store": str(store.pk)})) == [str(wanted.id)]

    @pytest.mark.parametrize("value", ["true", "1"])
    def test_today(self, approved: APIClient, value: str) -> None:
        wanted = _listing(start=NOW + timedelta(hours=2))
        _listing(start=NOW + timedelta(days=1))
        assert _ids(approved.get(URL, {"today": value})) == [str(wanted.id)]

    def test_today_false_lists_every_day(self, approved: APIClient) -> None:
        _listing()
        _listing(start=NOW + timedelta(days=1))
        assert len(_ids(approved.get(URL, {"today": "false"}))) == 2

    @pytest.mark.parametrize(
        ("params", "field"),
        [
            ({"store": "not-a-uuid"}, "store"),
            ({"today": "maybe"}, "today"),
            ({"category": "x" * 65}, "category"),
        ],
    )
    def test_an_invalid_filter_gets_400_naming_the_field(
        self, approved: APIClient, params: dict[str, str], field: str
    ) -> None:
        response = approved.get(URL, params)
        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "validation_error"
        assert body["message"] == "Check the highlighted fields."
        assert list(body["fields"]) == [field]


class TestPaging:
    def test_twenty_cards_a_page(self, approved: APIClient) -> None:
        store = StoreFactory()
        category = CategoryFactory()
        ListingFactory.create_batch(
            21,
            store=store,
            category=category,
            pickup_start=NOW + timedelta(hours=1),
            pickup_end=NOW + timedelta(hours=3),
        )

        first = approved.get(URL).json()
        second = approved.get(URL, {"page": 2}).json()

        assert first["count"] == 21
        assert len(first["results"]) == 20
        assert first["next"] is not None
        assert len(second["results"]) == 1
        assert second["next"] is None
        assert not set(_ids_of(first)) & set(_ids_of(second))

    def test_page_size_can_be_chosen(self, approved: APIClient) -> None:
        for _ in range(3):
            _listing()
        assert len(_ids(approved.get(URL, {"page_size": 2}))) == 2

    def test_a_page_past_the_end_gets_404(self, approved: APIClient) -> None:
        _listing()
        response = approved.get(URL, {"page": 2})
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"


def _ids_of(page: dict[str, Any]) -> list[str]:
    return [card["id"] for card in page["results"]]
