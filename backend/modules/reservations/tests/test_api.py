# AI contribution: 50% or more AI-generated
"""GET /api/listings/ (US-36): approved households browse, everyone else is refused.

Allowed: an active beneficiary whose own household is approved. Refused: signed
out (401), every other role, and a beneficiary whose household is missing, not
approved or expired (403).
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from adapters.photo_types import PhotoReadLink, PhotoStorageError
from modules.accounts.tests.factories import UserFactory
from modules.categories.tests.factories import CategoryFactory
from modules.households.tests.factories import HouseholdFactory
from modules.listings import photo_storage
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
    """Every request in these tests happens at NOW."""
    monkeypatch.setattr(timezone, "now", lambda: NOW)


@pytest.fixture
def client() -> APIClient:
    """An API client that asks for English messages."""
    return APIClient(HTTP_ACCEPT_LANGUAGE="en")


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


@pytest.fixture
def approved(client: APIClient) -> APIClient:
    """A client signed in, through a real session, as an approved household."""
    user = UserFactory(role="beneficiary")
    _household(user)
    client.force_login(user)
    return client


def _ids(response: Any) -> list[str]:
    """Listing IDs on the page, in order."""
    return [card["id"] for card in response.json()["results"]]


class TestApprovedHousehold:
    """Allowed: an active beneficiary whose household is approved."""

    # rule: BR-LIST-004
    def test_browses_only_visible_listings_as_cards(self, approved: APIClient) -> None:
        """Browses only visible listings as cards."""
        store: Any = StoreFactory(name="Épicerie Exemple")
        category = CategoryFactory(code="bakery")
        listing = _listing(
            store=store,
            category=category,
            quantity_total=5,
            quantity_reserved=2,
            max_per_household=2,
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
                    "max_per_household": 2,
                    "unit": "item",
                    "best_before": listing.best_before.isoformat(),
                    "photo_url": None,
                }
            ],
        }

    def test_cards_come_sorted_by_pickup_start(self, approved: APIClient) -> None:
        """Cards come sorted by pickup start."""
        later = _listing(start=NOW + timedelta(hours=4))
        sooner = _listing(start=NOW + timedelta(hours=1))
        assert _ids(approved.get(URL)) == [str(sooner.id), str(later.id)]

    def test_an_empty_list_is_still_a_page(self, approved: APIClient) -> None:
        """An empty list is still a page."""
        response = approved.get(URL)
        assert response.status_code == 200
        assert response.json() == {
            "count": 0,
            "next": None,
            "previous": None,
            "results": [],
        }

    def test_post_is_not_allowed(self, approved: APIClient) -> None:
        """POST gets 405 with a fixed message; the endpoint only reads."""
        response = approved.post(URL, {})
        assert response.status_code == 405
        assert response.json() == {
            "code": "method_not_allowed",
            "message": "Listings can only be read here.",
            "fields": {},
        }


class TestRefused:
    """Refused: signed out, every other role, and households not approved."""

    def test_signed_out_gets_401(self, client: APIClient) -> None:
        """A signed-out request gets 401 with a fixed message."""
        response = client.get(URL)
        assert response.status_code == 401
        assert response.json() == {
            "code": "not_authenticated",
            "message": "Sign in to see listings.",
            "fields": {},
        }

    @pytest.mark.parametrize(
        "role", ["store_staff", "store_manager", "intake_worker", "admin"]
    )
    def test_other_roles_get_403(self, client: APIClient, role: str) -> None:
        """Every role other than beneficiary gets 403."""
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
        """An inactive beneficiary account gets 403."""
        user = UserFactory(role="beneficiary", is_active=False)
        _household(user)
        client.force_authenticate(user)
        assert client.get(URL).status_code == 403

    # rule: BR-LIST-004
    @pytest.mark.parametrize("status", NOT_APPROVED_STATUSES)
    def test_a_household_that_is_not_approved_gets_403(
        self, client: APIClient, status: str
    ) -> None:
        """Each non-approved household status gets 403."""
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

    # rule: BR-LIST-004
    def test_an_expired_file_still_marked_approved_gets_403(
        self, client: APIClient
    ) -> None:
        """An approved file past its expiry gets 403."""
        user = UserFactory(role="beneficiary")
        _household(user, expires_at=NOW - timedelta(minutes=1))
        client.force_login(user)
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json()["code"] == "household_not_approved"

    def test_another_users_approved_household_does_not_let_you_browse(
        self, client: APIClient
    ) -> None:
        """Ownership: only the signed-in user's own household counts."""
        _household(UserFactory(role="beneficiary"))
        client.force_login(UserFactory(role="beneficiary"))
        _listing()
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json()["code"] == "household_not_approved"

    def test_refusal_comes_before_filter_validation(self, client: APIClient) -> None:
        """Refusal comes before filter validation."""
        client.force_login(UserFactory(role="beneficiary"))
        assert client.get(URL, {"store": "not-a-uuid"}).status_code == 403

    def test_the_refusal_is_in_french_by_default(self) -> None:
        """The refusal is in french by default."""
        client = APIClient()
        client.force_login(UserFactory(role="beneficiary"))
        response = client.get(URL)
        assert response.status_code == 403
        assert response.json()["message"] == NOT_APPROVED_FR


class TestFilters:
    """The category, store and today filters, and invalid values."""

    def test_category(self, approved: APIClient) -> None:
        """The category filter keeps only listings in that category."""
        wanted = _listing(category=CategoryFactory(code="bakery"))
        _listing()
        assert _ids(approved.get(URL, {"category": "bakery"})) == [str(wanted.id)]

    def test_store(self, approved: APIClient) -> None:
        """The store filter keeps only that store's listings."""
        store: Any = StoreFactory()
        wanted = _listing(store=store)
        _listing()
        assert _ids(approved.get(URL, {"store": str(store.pk)})) == [str(wanted.id)]

    # rule: BR-LIST-005
    @pytest.mark.parametrize("value", ["true", "1"])
    def test_today(self, approved: APIClient, value: str) -> None:
        """today=true or 1 keeps only pickups that start before Montreal midnight."""
        wanted = _listing(start=NOW + timedelta(hours=2))
        _listing(start=NOW + timedelta(days=1))
        assert _ids(approved.get(URL, {"today": value})) == [str(wanted.id)]

    # rule: BR-LIST-005
    def test_today_false_lists_every_day(self, approved: APIClient) -> None:
        """Today false lists every day."""
        _listing()
        _listing(start=NOW + timedelta(days=1))
        assert len(_ids(approved.get(URL, {"today": "false"}))) == 2

    @pytest.mark.parametrize(
        ("params", "field", "message"),
        [
            ({"store": "not-a-uuid"}, "store", "Enter a valid store ID."),
            ({"today": "maybe"}, "today", "Enter true or false."),
            (
                {"category": "x" * 65},
                "category",
                "Enter a category code of 1 to 64 characters.",
            ),
        ],
    )
    def test_an_invalid_filter_gets_400_with_a_fixed_message(
        self, approved: APIClient, params: dict[str, str], field: str, message: str
    ) -> None:
        """The message is ours; the value the user typed is never echoed back."""
        response = approved.get(URL, params)
        assert response.status_code == 400
        assert response.json() == {
            "code": "validation_error",
            "message": "Check the highlighted fields.",
            "fields": {field: [message]},
        }

    def test_a_filter_error_is_in_french_by_default(self) -> None:
        """A filter error is in french by default."""
        user = UserFactory(role="beneficiary")
        _household(user)
        client = APIClient()
        client.force_login(user)
        response = client.get(URL, {"store": "not-a-uuid"})
        assert response.status_code == 400
        assert response.json()["fields"] == {
            "store": ["Entrez un identifiant de commerce valide."]
        }


class TestPaging:
    """Always 20 cards a page (#506)."""

    def test_twenty_cards_a_page_whatever_page_size_asks(
        self, approved: APIClient
    ) -> None:
        """Twenty cards a page whatever page size asks."""
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
        asked_for_five = approved.get(URL, {"page_size": 5}).json()

        assert first["count"] == 21
        assert len(first["results"]) == 20
        assert first["next"] is not None
        assert len(second["results"]) == 1
        assert second["next"] is None
        assert not set(_ids_of(first)) & set(_ids_of(second))
        assert len(asked_for_five["results"]) == 20

    def test_a_page_past_the_end_gets_404(self, approved: APIClient) -> None:
        """A page past the end gets 404 with a fixed message."""
        _listing()
        response = approved.get(URL, {"page": 2})
        assert response.status_code == 404
        assert response.json() == {
            "code": "not_found",
            "message": "This page of listings does not exist.",
            "fields": {},
        }


def _ids_of(page: dict[str, Any]) -> list[str]:
    """Listing IDs in a decoded page, in order."""
    return [card["id"] for card in page["results"]]


def test_approved_household_gets_links_only_for_visible_photos(
    approved: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = "listing-photos/" + "a" * 32 + ".png"
    visible = _listing(photo_ref=reference)
    _listing(status="cancelled", photo_ref="listing-photos/" + "b" * 32 + ".png")
    no_photo = _listing()
    store = Mock()
    store.read_links.return_value = {
        reference: PhotoReadLink(
            "https://photos.example.test/read-token", NOW + timedelta(minutes=5)
        )
    }
    monkeypatch.setattr(photo_storage, "configured_store", lambda: store)
    response = approved.get(URL)
    assert response.status_code == 200
    cards = {row["id"]: row for row in response.json()["results"]}
    assert (
        cards[str(visible.pk)]["photo_url"] == "https://photos.example.test/read-token"
    )
    assert cards[str(no_photo.pk)]["photo_url"] is None
    assert "photo_ref" not in cards[str(visible.pk)]
    store.read_links.assert_called_once_with([reference])
    assert response["Cache-Control"] == "private, no-store"
    assert response["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize(
    "role",
    [None, "beneficiary", "store_staff", "store_manager", "intake_worker", "admin"],
)
def test_refused_users_never_receive_or_generate_photo_links(
    client: APIClient,
    role: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _listing(photo_ref="listing-photos/" + "a" * 32 + ".png")
    factory = Mock()
    monkeypatch.setattr(photo_storage, "configured_store", factory)
    if role:
        store = StoreFactory() if role in {"store_staff", "store_manager"} else None
        client.force_login(UserFactory(role=role, store=store))
    response = client.get(URL)
    assert response.status_code in {401, 403}
    factory.assert_not_called()
    assert "photo_url" not in response.json()


def test_browse_without_photos_does_not_initialize_storage(
    approved: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = Mock()
    monkeypatch.setattr(photo_storage, "configured_store", factory)
    for _ in range(2):
        response = approved.get(URL)
        assert response.status_code == 200
        _listing()
    factory.assert_not_called()


def test_only_current_page_photos_are_signed_in_one_batch(
    approved: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    references = [f"listing-photos/{index:032x}.png" for index in range(21)]
    for index, reference in enumerate(references):
        _listing(start=NOW + timedelta(hours=1, minutes=index), photo_ref=reference)
    store = Mock()
    store.read_links.return_value = {
        reference: PhotoReadLink(
            f"https://photos.example.test/{reference}", NOW + timedelta(minutes=5)
        )
        for reference in references
    }
    factory = Mock(return_value=store)
    monkeypatch.setattr(photo_storage, "configured_store", factory)
    first = approved.get(URL)
    assert first.status_code == 200
    assert len(first.json()["results"]) == 20
    factory.assert_called_once()
    store.read_links.assert_called_once_with(references[:20])
    factory.reset_mock()
    store.read_links.reset_mock()
    second = approved.get(URL, {"page": 2})
    assert second.status_code == 200
    assert len(second.json()["results"]) == 1
    factory.assert_called_once()
    store.read_links.assert_called_once_with(references[20:])


@pytest.mark.parametrize(
    "backend", ["", "missing.module.factory", "adapters.blob_photos.BlobPhotoStore"]
)
def test_storage_configuration_failure_keeps_listings_available_without_photos(
    approved: APIClient, settings: Any, backend: str
) -> None:
    _listing(photo_ref="listing-photos/" + "a" * 32 + ".png")
    settings.LISTING_PHOTO_STORE_BACKEND = backend
    response = approved.get(URL)
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["photo_url"] is None


@pytest.mark.parametrize(
    "language",
    ["en", "fr"],
)
def test_photo_link_failure_keeps_listing_details_and_does_not_leak_reference(
    approved: APIClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    language: str,
) -> None:
    """An optional photo outage must not hide authorized listing details."""
    reference = "listing-photos/" + "a" * 32 + ".png"
    listing = _listing(photo_ref=reference)
    store = Mock()
    store.read_links.side_effect = PhotoStorageError("private storage credentials")
    monkeypatch.setattr(photo_storage, "configured_store", lambda: store)
    response = approved.get(URL, HTTP_ACCEPT_LANGUAGE=language)
    assert response.status_code == 200
    card = response.json()["results"][0]
    assert card["id"] == str(listing.pk)
    assert card["title"] == listing.title
    assert card["photo_url"] is None
    assert reference not in str(response.json())
    assert "private storage credentials" not in caplog.text
    assert "listing_photo_read_failed" in [
        getattr(record, "event", None) for record in caplog.records
    ]
