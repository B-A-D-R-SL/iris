# AI contribution: 50% or more AI-generated
"""US-35 (T-05.35.1) seen from listings: a category in use is deactivated, never
deleted, and a deactivated category can no longer be used to post a listing."""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from modules.categories import services as category_services
from modules.categories.models import Category
from modules.listings import services
from modules.listings.models import Listing
from modules.listings.tests.factories import ListingFactory

pytestmark = pytest.mark.django_db


def _admin() -> Any:
    return get_user_model().objects.create_user(
        email="category-admin@example.test", password="unused-password-1", role="admin"
    )


def _admin_client() -> APIClient:
    client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    client.force_authenticate(user=_admin())
    return client


def test_a_category_in_use_is_deactivated_not_deleted() -> None:
    listing = cast(Listing, ListingFactory())
    category = listing.category
    url = reverse("staff-category-detail", kwargs={"code": category.code})
    client = _admin_client()

    deleted = client.delete(url)
    deactivated = client.patch(url, {"is_active": False}, format="json")

    assert deleted.status_code == 405
    assert deactivated.status_code == 200
    category.refresh_from_db()
    assert category.is_active is False
    # The listing keeps its category; nothing was deleted.
    assert Listing.objects.get(pk=listing.pk).category_id == category.pk
    public = APIClient().get(reverse("categories-list")).json()
    assert category.code not in [item["code"] for item in public]


def test_posting_with_a_deactivated_category_is_refused(
    posting_case: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    category_services.update_category(
        posting_case.category.code, {"is_active": False}, _admin()
    )
    monkeypatch.setattr(services, "_safety_checker", lambda: Mock(return_value=[]))
    store_client = APIClient(HTTP_ACCEPT_LANGUAGE="en")
    store_client.force_authenticate(user=posting_case.user)

    response = store_client.post(
        reverse("store-listing-create"),
        {
            "title": posting_case.data.title,
            "category": posting_case.category.code,
            "quantity": posting_case.data.quantity,
            "pickup_start": posting_case.data.pickup_start.isoformat(),
            "pickup_end": posting_case.data.pickup_end.isoformat(),
            "best_before": posting_case.data.best_before.isoformat(),
            "safe_and_allowed": True,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "category" in response.data["fields"]
    assert not Listing.objects.exists()


def test_posting_works_again_after_reactivation(
    posting_case: SimpleNamespace,
) -> None:
    admin = _admin()
    category_services.update_category(
        posting_case.category.code, {"is_active": False}, admin
    )
    category_services.update_category(
        posting_case.category.code, {"is_active": True}, admin
    )

    assert Category.objects.get(code=posting_case.category.code).is_active is True
    assert posting_case.category.code in [
        item["code"] for item in APIClient().get(reverse("categories-list")).json()
    ]
