# AI contribution: 50% or more AI-generated
"""The authentication API serves browser clients only."""

import pytest
from django.conf import settings


@pytest.mark.parametrize("method", ["get", "post", "delete"])
@pytest.mark.parametrize(
    "path", ["config", "auth/login", "auth/session", "tokens/refresh"]
)
def test_app_auth_routes_are_removed(client, method, path):
    assert settings.HEADLESS_CLIENTS == ("browser",)
    response = getattr(client, method)(f"/api/auth/app/v1/{path}")
    assert response.status_code == 404


def test_browser_config_remains_available(client):
    assert client.get("/api/auth/browser/v1/config").status_code == 200
