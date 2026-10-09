import json

import django
from django.conf import settings
from django.test import Client
from django.urls import reverse


def test_django_version():
    assert django.get_version().startswith("6.1.")


def test_required_apps_installed():
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "drf_spectacular" in settings.INSTALLED_APPS
    assert "allauth" in settings.INSTALLED_APPS


def test_api_schema_route():
    assert reverse("schema") == "/api/schema/"


def test_health_endpoint(client: Client) -> None:
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "ok"}