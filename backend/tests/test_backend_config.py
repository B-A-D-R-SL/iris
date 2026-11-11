# AI contribution: 50% or more AI-generated
import json
import os
import subprocess
import sys

import django
import pytest
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


@pytest.mark.parametrize("timeout", ["0", "-1", "25"])
def test_duplicate_lock_timeout_must_be_positive(timeout):
    result = subprocess.run(
        [sys.executable, "-c", "import iris.settings.base"],
        env={**os.environ, "HOUSEHOLD_DUPLICATE_LOCK_TIMEOUT_MS": timeout},
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if timeout == "25":
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
        assert "HOUSEHOLD_DUPLICATE_LOCK_TIMEOUT_MS must be positive." in result.stderr


def test_health_endpoint(client: Client) -> None:
    response = client.get("/api/health/")

    assert response.status_code == 200
    assert json.loads(response.content) == {"status": "ok"}


@pytest.mark.parametrize(
    "settings_module",
    ["iris.settings.test", "iris.settings.production", "iris.settings.local"],
)
@pytest.mark.parametrize(
    ("entrypoint", "configured_max_age", "expected_max_age"),
    [("asgi", "60", 0), ("asgi", "120", 0), ("wsgi", "60", 60), ("wsgi", "0", 0)],
)
def test_entrypoint_connection_policy(
    settings_module, entrypoint, configured_max_age, expected_max_age
):
    env = {**os.environ}
    env.pop("IRIS_SERVER_INTERFACE", None)
    env.update(
        DJANGO_SETTINGS_MODULE=settings_module,
        DJANGO_SECRET_KEY="connection-policy-subprocess-test-key-0123456789-ABCDEF",
        DJANGO_ALLOWED_HOSTS="localhost",
        DATABASE_CONN_MAX_AGE=configured_max_age,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                f"import iris.{entrypoint}; from django.conf import settings; "
                "import json, os; print(json.dumps({"
                "'max_age': settings.DATABASES['default']['CONN_MAX_AGE'], "
                "'configured': os.environ['DATABASE_CONN_MAX_AGE']}))"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    assert json.loads(result.stdout) == {
        "max_age": 0 if settings_module == "iris.settings.local" else expected_max_age,
        "configured": configured_max_age,
    }
