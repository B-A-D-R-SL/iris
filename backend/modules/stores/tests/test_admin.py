# AI contribution: 50% or more AI-generated
# Code has been planned and written by AI, while I reviewed, edited, and tested the code
"""US-11 admin access and HTTP-to-database integration tests."""

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse
from modules.stores.models import Store

LOCAL_ADMIN_EMAIL = "admin@iris.local"
LOCAL_ADMIN_PASSWORD = "iris_local_admin_password"


@pytest.mark.django_db
def test_local_admin_can_see_and_edit_seeded_badr_store(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use the documented local login and confirm that an edit reaches PostgreSQL."""
    monkeypatch.setenv("DJANGO_DEV_ADMIN_EMAIL", LOCAL_ADMIN_EMAIL)
    monkeypatch.setenv("DJANGO_DEV_ADMIN_PASSWORD", LOCAL_ADMIN_PASSWORD)
    with override_settings(DEBUG=True):
        call_command("create_dev_admin", stdout=StringIO())
    call_command("seed_badr_store", stdout=StringIO())

    store = Store.objects.get(is_badr=True)
    assert client.login(username=LOCAL_ADMIN_EMAIL, password=LOCAL_ADMIN_PASSWORD)

    list_url = reverse("admin:stores_store_changelist")
    change_url = reverse("admin:stores_store_change", args=[store.pk])
    listing = client.get(list_url)
    assert listing.status_code == 200
    assert b"B.A.D.R." in listing.content
    assert client.get(change_url).status_code == 200

    response = client.post(
        change_url,
        {
            "name": store.name,
            "street_number": store.street_number,
            "street_name": store.street_name,
            "unit": store.unit or "",
            "city": store.city,
            "postal_code": store.postal_code,
            "phone": "514-555-0199",
            "email": store.email,
            "opening_hours": "{}",
            "pickup_instructions": store.pickup_instructions or "",
            "is_badr": "on",
            "is_active": "on",
            "_save": "Save",
        },
    )

    assert response.status_code == 302, response.context[
        "adminform"
    ].form.errors.as_json()
    store.refresh_from_db()
    assert store.phone == "514-555-0199"


@pytest.mark.django_db
def test_non_admins_cannot_view_or_edit_store_in_admin(client: Client) -> None:
    """Require Django administrator privileges for store admin pages."""
    call_command("seed_badr_store", stdout=StringIO())
    store = Store.objects.get(is_badr=True)
    list_url = reverse("admin:stores_store_changelist")
    change_url = reverse("admin:stores_store_change", args=[store.pk])

    assert client.get(list_url).status_code == 302
    assert client.get(change_url).status_code == 302

    user_model = get_user_model()
    ordinary_user = user_model._default_manager.create_user(
        username="non-admin@example.test", password="local-test-password"
    )
    client.force_login(ordinary_user)

    assert client.get(list_url).status_code == 302
    assert client.get(change_url).status_code == 302
    assert client.post(change_url, {"phone": "514-555-0199"}).status_code == 302
    store.refresh_from_db()
    assert store.phone != "514-555-0199"
