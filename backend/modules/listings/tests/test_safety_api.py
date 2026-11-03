# AI contribution: 50% or more AI-generated
"""US-34 over HTTP and PostgreSQL: real safety rule, posting categories endpoint."""

import json
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation
from rest_framework.test import APIClient

from modules.categories.tests.factories import CategoryFactory
from modules.listings.models import Listing
from modules.listings.tests.test_post_listing_api import payload
from modules.rules import queries as rule_queries
from modules.rules.models import RuleSetVersion
from modules.rules.services import publish

CATEGORIES_URL = "store-listing-categories"


@pytest.fixture
def store_client(posting_case: SimpleNamespace) -> APIClient:
    """A store worker's client; unlike US-33's, the real safety rule runs."""
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    client.credentials(HTTP_ACCEPT_LANGUAGE="en")
    return client


def ban(case: SimpleNamespace, *codes: str) -> None:
    publish(
        "listing_safety",
        {"best_before_margin_days": 0, "prohibited_category_codes": list(codes)},
        case.user,
        effective_from=case.now,
    )


# --- POST /api/store/listings/ with the real safety rule -------------------


def test_us34_api_main_path_publishes_and_stores_who_and_when(
    posting_case: SimpleNamespace, store_client: APIClient
) -> None:
    response = store_client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 201
    saved = Listing.objects.get(pk=response.json()["id"])
    assert saved.safe_confirmed_by_id == posting_case.user.pk
    assert saved.safe_confirmed_at == posting_case.now
    assert response.json()["safe_confirmed_at"].endswith("Z")


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Choose Oct. 27, 2026 or later (end of pickup)."),
        ("fr", "Choisissez le 27 oct. 2026 ou après (fin de la cueillette)."),
    ],
)
def test_us34_api_refuses_early_best_before_in_user_language(
    posting_case: SimpleNamespace,
    store_client: APIClient,
    language: str,
    expected: str,
) -> None:
    store_client.credentials(HTTP_ACCEPT_LANGUAGE=language)
    early = posting_case.data.best_before - timedelta(days=1)
    response = store_client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), "best_before": early.isoformat()},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["fields"] == {"best_before": [expected]}
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Enter a best-before date. It is required for food."),
        (
            "fr",
            "Entrez une date de meilleur avant. Elle est obligatoire pour les aliments.",
        ),
    ],
)
def test_us34_api_refuses_food_without_best_before(
    posting_case: SimpleNamespace,
    store_client: APIClient,
    language: str,
    expected: str,
) -> None:
    store_client.credentials(HTTP_ACCEPT_LANGUAGE=language)
    response = store_client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), "best_before": None},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["fields"] == {"best_before": [expected]}


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "This category can't be posted. Choose another one."),
        ("fr", "Cette catégorie ne peut pas être publiée. Choisissez-en une autre."),
    ],
)
def test_us34_api_refuses_prohibited_category(
    posting_case: SimpleNamespace,
    store_client: APIClient,
    language: str,
    expected: str,
) -> None:
    store_client.credentials(HTTP_ACCEPT_LANGUAGE=language)
    ban(posting_case, posting_case.category.code)
    response = store_client.post(
        reverse("store-listing-create"),
        payload(posting_case),
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["fields"] == {"category": [expected]}
    assert not Listing.objects.exists()


# Stored values that publish() would refuse; written directly to simulate a
# corrupted row. The non-object one used to raise AttributeError (500).
MALFORMED_VALUES = [
    {"best_before_margin_days": 0},
    {"best_before_margin_days": -1, "prohibited_category_codes": []},
    [],
]


def store_malformed_rule(case: SimpleNamespace, values: Any) -> None:
    RuleSetVersion.objects.create(
        rule_type="listing_safety",
        version=2,
        values=values,
        effective_from=case.now,
        created_by=case.user,
    )


@pytest.mark.parametrize("values", MALFORMED_VALUES)
def test_us34_api_malformed_safety_rules_return_503(
    posting_case: SimpleNamespace, store_client: APIClient, values: Any
) -> None:
    store_malformed_rule(posting_case, values)
    response = store_client.post(
        reverse("store-listing-create"), payload(posting_case), format="json"
    )
    assert response.status_code == 503
    assert response.json() == {
        "code": "posting_unavailable",
        "message": "Listing safety rules need configuration.",
        "fields": {},
    }
    assert not Listing.objects.exists()


# --- GET /api/store/listings/categories/ ------------------------------------


@pytest.mark.parametrize("role", ["store_staff", "store_manager"])
def test_us34_categories_lists_active_postable_categories(
    posting_case: SimpleNamespace, store_client: APIClient, role: str
) -> None:
    posting_case.user.role = role
    clothing = CategoryFactory(is_food=False, code="clothing_example")
    CategoryFactory(is_active=False, code="inactive_example")
    response = store_client.get(reverse(CATEGORIES_URL))
    assert response.status_code == 200
    assert response.json() == [
        {
            "code": clothing.code,
            "name_fr": clothing.name_fr,
            "name_en": clothing.name_en,
            "is_food": False,
            "default_value_cents": clothing.default_value_cents,
        },
        {
            "code": posting_case.category.code,
            "name_fr": posting_case.category.name_fr,
            "name_en": posting_case.category.name_en,
            "is_food": True,
            "default_value_cents": posting_case.category.default_value_cents,
        },
    ]


# rule: BR-LIST-002 categories on the prohibited list cannot be selected (AC3)
def test_us34_categories_leaves_out_prohibited_codes(
    posting_case: SimpleNamespace, store_client: APIClient
) -> None:
    allowed = CategoryFactory(code="allowed_example")
    ban(posting_case, posting_case.category.code)
    response = store_client.get(reverse(CATEGORIES_URL))
    assert response.status_code == 200
    assert [c["code"] for c in response.json()] == [allowed.code]


@pytest.mark.parametrize(
    "role", ["beneficiary", "intake_worker", "admin", "invalid", None]
)
def test_us34_categories_refuses_other_roles(
    posting_case: SimpleNamespace, store_client: APIClient, role: str | None
) -> None:
    posting_case.user.role = role
    response = store_client.get(reverse(CATEGORIES_URL))
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_us34_categories_refuses_anonymous_user(posting_case: SimpleNamespace) -> None:
    response = APIClient().get(reverse(CATEGORIES_URL))
    assert response.status_code == 403


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_us34_categories_is_read_only(
    posting_case: SimpleNamespace, store_client: APIClient, method: str
) -> None:
    response = getattr(store_client, method)(reverse(CATEGORIES_URL), {}, format="json")
    assert response.status_code == 405


def test_us34_categories_without_safety_rules_returns_503(
    posting_case: SimpleNamespace,
    store_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Published versions cannot be deleted; simulate "none in effect yet".
    monkeypatch.setattr(rule_queries, "active", lambda rule_type, at=None: None)
    response = store_client.get(reverse(CATEGORIES_URL))
    assert response.status_code == 503
    assert response.json()["code"] == "posting_unavailable"


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Listing safety rules need configuration."),
        ("fr", "Les règles de sécurité des offres doivent être configurées."),
    ],
)
def test_us34_categories_with_malformed_rules_returns_503(
    posting_case: SimpleNamespace,
    store_client: APIClient,
    language: str,
    expected: str,
) -> None:
    store_client.credentials(HTTP_ACCEPT_LANGUAGE=language)
    store_malformed_rule(
        posting_case, {"best_before_margin_days": 0, "prohibited_category_codes": "x"}
    )
    response = store_client.get(reverse(CATEGORIES_URL))
    assert response.status_code == 503
    assert response.json()["message"] == expected


@pytest.mark.parametrize("values", MALFORMED_VALUES)
def test_us34_categories_checks_the_same_rule_as_posting(
    posting_case: SimpleNamespace, store_client: APIClient, values: Any
) -> None:
    # A rule that would block every post also blocks the form from opening.
    store_malformed_rule(posting_case, values)
    response = store_client.get(reverse(CATEGORIES_URL))
    assert response.status_code == 503
    assert response.json() == {
        "code": "posting_unavailable",
        "message": "Listing safety rules need configuration.",
        "fields": {},
    }


def test_us34_schema_documents_posting_categories(client: Client) -> None:
    with translation.override("en"):
        response = client.get(
            reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
        )
    schema: dict[str, Any] = json.loads(response.content)
    operation = schema["paths"][reverse(CATEGORIES_URL)]["get"]
    assert operation["operationId"] == "store_listings_categories_list"
    assert set(operation["responses"]) == {"200", "403", "503"}
    assert set(schema["paths"][reverse(CATEGORIES_URL)]) == {"get"}
