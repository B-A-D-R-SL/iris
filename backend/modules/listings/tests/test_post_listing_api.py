# AI contribution: 50% or more AI-generated
"""HTTP-to-PostgreSQL checks with explicit test-only account/safety stand-ins."""

import json
import sys
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import translation
from rest_framework.test import APIClient

from modules.listings import services
from modules.listings.domain.posting import Refusal
from modules.listings.models import Listing
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.models import RuleSetVersion


def payload(case: SimpleNamespace) -> dict[str, Any]:
    return {
        "title": case.data.title,
        "category": case.category.code,
        "quantity": case.data.quantity,
        "pickup_start": case.data.pickup_start.isoformat(),
        "pickup_end": case.data.pickup_end.isoformat(),
        "best_before": case.data.best_before.isoformat(),
        "safe_and_allowed": True,
    }


@pytest.fixture
def posting_client(
    posting_case: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> APIClient:
    # force_authenticate bypasses login only. View/service authorization and the
    # real database still run. Nothing adds roles to real users in the app.
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    client.credentials(HTTP_ACCEPT_LANGUAGE="en")
    monkeypatch.setattr(services, "_safety_checker", lambda: Mock(return_value=[]))
    return client


def test_us33_api_publishes_and_returns_store_location(
    posting_case: SimpleNamespace, posting_client: APIClient
) -> None:
    case = posting_case
    response = posting_client.post(
        reverse("store-listing-create"), payload(case), format="json"
    )
    assert response.status_code == 201
    body = response.json()
    saved = Listing.objects.get(pk=body["id"])
    assert body["quantity"] == saved.quantity_total == 5
    assert body["quantity_reserved"] == 0
    assert body["status"] == "published"
    assert body["category"] == case.category.code
    assert saved.category_id == case.category.pk
    assert body["location"] == {
        "street_number": case.store.street_number,
        "street_name": case.store.street_name,
        "unit": case.store.unit,
        "city": case.store.city,
        "postal_code": case.store.postal_code,
    }
    assert saved.store_id == case.store.pk
    assert saved.safe_confirmed_by_id == case.user.pk
    assert body["pickup_start"].endswith("Z")
    assert body["published_at"].endswith("Z")
    assert body["safe_confirmed_at"] == body["published_at"]
    assert body["unit"] == "item"
    assert body["max_per_household"] == 1
    assert "photo_ref" not in body


def test_us33_api_defaults_quantity_and_keeps_optional_values(
    posting_case: SimpleNamespace, posting_client: APIClient
) -> None:
    data = payload(posting_case)
    data.pop("quantity")
    data.update(
        description="A sealed bundle",
        unit="bundle",
        max_per_household=2,
        estimated_value_cents=1250,
    )
    response = posting_client.post(reverse("store-listing-create"), data, format="json")
    assert response.status_code == 201
    saved = Listing.objects.get()
    assert saved.quantity_total == 1
    assert saved.description == "A sealed bundle"
    assert saved.unit == "bundle"
    assert saved.max_per_household == 2
    assert saved.estimated_value_cents == 1250


@pytest.mark.parametrize(
    "role", ["beneficiary", "intake_worker", "admin", "invalid", None]
)
def test_us33_api_refuses_other_roles(
    posting_case: SimpleNamespace, posting_client: APIClient, role: str | None
) -> None:
    posting_case.user.role = role
    response = posting_client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 403
    assert not Listing.objects.exists()


@pytest.mark.parametrize("role", ["store_staff", "store_manager"])
def test_us33_api_accepts_posting_roles(
    posting_case: SimpleNamespace, posting_client: APIClient, role: str
) -> None:
    posting_case.user.role = role
    response = posting_client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 201


def test_us33_api_refuses_anonymous_user(posting_case: SimpleNamespace) -> None:
    response = APIClient().post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 403
    assert not Listing.objects.exists()


def test_us33_api_default_user_has_no_implicit_store_assignment(
    posting_case: SimpleNamespace,
) -> None:
    client = APIClient()
    client.force_authenticate(
        user=get_user_model().objects.get(pk=posting_case.user.pk)
    )
    response = client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 403
    assert not Listing.objects.exists()


def test_us33_api_refuses_other_store(
    posting_case: SimpleNamespace,
    posting_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post = Mock()
    monkeypatch.setattr(services, "post_listing", post)
    response = posting_client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), "store": str(uuid4())},
        format="json",
    )
    assert response.status_code == 403
    post.assert_not_called()
    assert not Listing.objects.exists()


def test_us33_api_refuses_inactive_store(
    posting_case: SimpleNamespace, posting_client: APIClient
) -> None:
    posting_case.store.is_active = False
    posting_case.store.save()
    response = posting_client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 403
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    "field",
    [
        "status",
        "quantity_reserved",
        "created_by",
        "safe_confirmed_by",
        "safe_confirmed_at",
        "published_at",
        "location",
        "photo_ref",
    ],
)
def test_us33_api_refuses_server_owned_fields(
    posting_case: SimpleNamespace, posting_client: APIClient, field: str
) -> None:
    response = posting_client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), field: "forged"},
        format="json",
    )
    assert response.status_code == 400
    assert field in response.json()["fields"]
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"title": "X"}, "title"),
        ({"quantity": 1000}, "quantity"),
        ({"max_per_household": 11}, "max_per_household"),
        ({"unit": "box"}, "unit"),
        ({"estimated_value_cents": -1}, "estimated_value_cents"),
        ({"safe_and_allowed": False}, "safe_and_allowed"),
        ({"category": "no_such_category"}, "category"),
        ({"category": ""}, "category"),
        ({"pickup_start": "2026-10-27T20:00:00"}, "pickup_start"),
        ({"pickup_end": "2026-10-27T19:01:00Z"}, "pickup_end"),
    ],
)
def test_us33_api_returns_field_errors(
    posting_case: SimpleNamespace,
    posting_client: APIClient,
    changes: dict[str, Any],
    field: str,
) -> None:
    response = posting_client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), **changes},
        format="json",
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert isinstance(body["fields"][field], list)
    assert not Listing.objects.exists()


def test_us33_api_requires_confirmation_field(
    posting_case: SimpleNamespace, posting_client: APIClient
) -> None:
    data = payload(posting_case)
    data.pop("safe_and_allowed")
    response = posting_client.post(reverse("store-listing-create"), data, format="json")
    assert response.status_code == 400
    assert "safe_and_allowed" in response.json()["fields"]


def test_us33_api_applies_safety_refusals(
    posting_case: SimpleNamespace,
    posting_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        services,
        "_safety_checker",
        lambda: Mock(return_value=[Refusal("best_before", "unsafe_listing")]),
    )
    response = posting_client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 400
    assert "best_before" in response.json()["fields"]
    assert not Listing.objects.exists()


def test_us33_api_missing_safety_returns_503_without_publishing(
    posting_case: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "modules.listings.domain.safety", None)
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    response = client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 503
    assert response.json()["code"] == "posting_unavailable"
    assert not Listing.objects.exists()


@pytest.mark.parametrize("configuration_error", ["missing_key", "unexpected_key"])
@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Listing posting rules need configuration."),
        ("fr", "Les règles de publication des offres doivent être configurées."),
    ],
)
def test_us33_api_malformed_posting_rules_return_503_without_publishing(
    posting_case: SimpleNamespace,
    posting_client: APIClient,
    configuration_error: str,
    language: str,
    expected: str,
) -> None:
    values = deepcopy(DEFAULT_RULE_VALUES["listing_posting"])
    if configuration_error == "missing_key":
        values.pop("quantity_max")
    else:
        values["unexpected_limit"] = 1
    RuleSetVersion.objects.create(
        rule_type="listing_posting",
        version=2,
        values=values,
        effective_from=posting_case.now,
        created_by=posting_case.user,
    )
    posting_client.credentials(HTTP_ACCEPT_LANGUAGE=language)
    response = posting_client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 503
    assert response.json() == {
        "code": "posting_unavailable",
        "message": expected,
        "fields": {},
    }
    assert not Listing.objects.exists()


def test_us33_real_session_requires_csrf_token(posting_case: SimpleNamespace) -> None:
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(posting_case.user)
    response = client.post(
        reverse("store-listing-create"),
        payload(posting_case),
        format="json",
        HTTP_ACCEPT_LANGUAGE="en",
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["message"]
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Tick this box to publish."),
        ("fr", "Cochez cette case pour publier."),
    ],
)
def test_us33_api_translates_validation_errors(
    posting_case: SimpleNamespace,
    posting_client: APIClient,
    language: str,
    expected: str,
) -> None:
    posting_client.credentials(HTTP_ACCEPT_LANGUAGE=language)
    response = posting_client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), "safe_and_allowed": False},
        format="json",
        HTTP_ACCEPT_LANGUAGE=language,
    )
    assert response.status_code == 400
    assert response.json()["fields"]["safe_and_allowed"] == [expected]


def test_us33_schema_documents_post_and_errors(client: Client) -> None:
    with translation.override("en"):
        response = client.get(
            reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
        )
    schema = json.loads(response.content)
    operation = schema["paths"][reverse("store-listing-create")]["post"]
    assert operation["operationId"] == "store_listings_create"
    assert set(operation["responses"]) == {"201", "400", "403", "503"}
    assert {"cookieAuth": []} in operation["security"]
    assert (
        schema["components"]["schemas"]["NewListing"]["properties"]["photo"]["format"]
        == "binary"
    )
    posted_listing = schema["components"]["schemas"]["PostedListing"]
    assert "photo_ref" not in posted_listing["properties"]
    assert "photo_ref" not in posted_listing.get("required", [])


def test_us33_collection_does_not_implement_browsing_yet(
    posting_case: SimpleNamespace, posting_client: APIClient
) -> None:
    assert posting_client.get(reverse("store-listing-create")).status_code == 405
