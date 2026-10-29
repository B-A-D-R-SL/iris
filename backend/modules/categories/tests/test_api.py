# AI contribution: 50% or more AI-generated
"""Tests for the public Categories REST API."""

import pytest
from django.test import Client
from django.urls import reverse

from modules.categories.models import Category
from modules.categories.services import save_category


@pytest.mark.django_db
def test_categories_endpoint_is_public(client: Client) -> None:
    """Unauthenticated visitors can access categories."""
    response = client.get(reverse("categories-list"))

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_categories_returns_active_categories(client: Client) -> None:
    """Inactive categories must not appear in public results."""
    save_category(
        Category(
            code="bakery",
            name_fr="Boulangerie",
            name_en="Bakery",
            is_food=True,
            default_value_cents=400,
        )
    )

    save_category(
        Category(
            code="inactive",
            name_fr="Inactif",
            name_en="Inactive",
            is_food=False,
            default_value_cents=500,
            is_active=False,
        )
    )

    response = client.get(reverse("categories-list"))

    assert response.status_code == 200
    assert response.json() == [
        {
            "code": "bakery",
            "name_fr": "Boulangerie",
            "name_en": "Bakery",
            "is_food": True,
            "default_value_cents": 400,
        }
    ]


def test_categories_rejects_post(client: Client) -> None:
    """Public users cannot create categories through this endpoint."""
    response = client.post(
        reverse("categories-list"),
        data={},
    )

    assert response.status_code == 405


def test_categories_appears_in_openapi(client: Client) -> None:
    """The categories endpoint must appear in API documentation."""
    response = client.get(
        reverse("schema"),
        HTTP_ACCEPT="application/vnd.oai.openapi+json",
    )

    assert response.status_code == 200

    paths = response.json()["paths"]
    assert "/api/categories/" in paths
    assert "get" in paths["/api/categories/"]
    assert "post" not in paths["/api/categories/"]
