# AI contribution: 50% or more AI-generated
"""GET /api/listings/ photo links (FIX-02): signed only for visible listings, never leaked.

Moved unchanged from test_api.py to keep each file under 500 lines.
"""

from datetime import timedelta
from typing import Any
from unittest.mock import Mock

import pytest
from rest_framework.test import APIClient

from adapters.photo_types import PhotoReadLink, PhotoStorageError
from modules.accounts.tests.factories import UserFactory
from modules.listings import photo_storage
from modules.reservations.tests.browse.helpers import NOW, URL, _listing
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db


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
