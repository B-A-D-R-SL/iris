# AI contribution: 50% or more AI-generated
import json
import os
import subprocess
import sys

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


def test_asgi_disables_wsgi_connection_persistence():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import iris.asgi; from django.conf import settings; "
                "print(settings.DATABASES['default']['CONN_MAX_AGE'])"
            ),
        ],
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "iris.settings.test",
            "DATABASE_CONN_MAX_AGE": "60",
        },
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert result.stdout.strip() == "0"
