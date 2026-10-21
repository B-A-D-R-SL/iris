# AI contribution: 50% or more AI-generated
"""US-11 admin-only Store REST API and OpenAPI contract tests."""

import json
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client, override_settings
from modules.stores.models import Store

LOCAL_ADMIN_EMAIL = "admin@iris.local"
LOCAL_ADMIN_PASSWORD = "iris_local_admin_password"


def _seed_store() -> Store:
    """Create the B.A.D.R. store through its planned management command."""
    call_command("seed_badr_store", stdout=StringIO())
    return Store.objects.get(is_badr=True)


@pytest.mark.django_db
def test_admin_store_api_reads_and_updates_the_database(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read the seeded store and persist a PATCH through the REST endpoint."""
    monkeypatch.setenv("DJANGO_DEV_ADMIN_EMAIL", LOCAL_ADMIN_EMAIL)
    monkeypatch.setenv("DJANGO_DEV_ADMIN_PASSWORD", LOCAL_ADMIN_PASSWORD)
    with override_settings(DEBUG=True):
        call_command("create_dev_admin", stdout=StringIO())
    store = _seed_store()
    assert client.login(username=LOCAL_ADMIN_EMAIL, password=LOCAL_ADMIN_PASSWORD)

    url = f"/api/staff/stores/{store.pk}/"
    response = client.get(url, HTTP_ACCEPT="application/json")
    assert response.status_code == 200
    assert response.json()["is_badr"] is True
    assert response.json()["name"] == "B.A.D.R."

    response = client.patch(
        url,
        data=json.dumps({"phone": "514-555-0199"}),
        content_type="application/json",
    )
    assert response.status_code == 200
    store.refresh_from_db()
    assert store.phone == "514-555-0199"


@pytest.mark.django_db
@pytest.mark.parametrize("method", ["get", "patch"])
def test_store_api_refuses_anonymous_and_non_admin_users(
    client: Client, method: str
) -> None:
    """Apply the admin-only permission to both Store REST operations."""
    store = _seed_store()
    url = f"/api/staff/stores/{store.pk}/"

    def request() -> HttpResponse:
        if method == "patch":
            return client.patch(
                url,
                data=json.dumps({"phone": "514-555-0199"}),
                content_type="application/json",
            )
        return client.get(url)

    assert request().status_code in {401, 403}
    ordinary_user = get_user_model()._default_manager.create_user(
        username="non-admin@example.test", password="local-test-password"
    )
    client.force_login(ordinary_user)
    assert request().status_code == 403
    store.refresh_from_db()
    assert store.phone != "514-555-0199"


@pytest.mark.django_db
def test_store_api_is_documented_in_openapi_schema(client: Client) -> None:
    """Expose the admin Store GET and PATCH operations in Swagger's schema."""
    response = client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    operations = response.json()["paths"]["/api/staff/stores/{id}/"]
    assert {"get", "patch"} <= set(operations)
