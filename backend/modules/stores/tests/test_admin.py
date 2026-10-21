# AI contribution: 50% or more AI-generated
"""US-11 Django admin registration, form, and permission tests."""

from io import StringIO

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.test import RequestFactory, override_settings
from django.urls import reverse
from modules.stores.models import Store

LOCAL_ADMIN_EMAIL = "admin@iris.local"
LOCAL_ADMIN_PASSWORD = "iris_local_admin_password"


@pytest.mark.django_db
def test_local_admin_can_see_and_edit_store_in_django_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check the registered admin form and persist an edit without HTTP requests."""
    monkeypatch.setenv("DJANGO_DEV_ADMIN_EMAIL", LOCAL_ADMIN_EMAIL)
    monkeypatch.setenv("DJANGO_DEV_ADMIN_PASSWORD", LOCAL_ADMIN_PASSWORD)
    with override_settings(DEBUG=True):
        call_command("create_dev_admin", stdout=StringIO())
    admin_user = get_user_model()._default_manager.get(username=LOCAL_ADMIN_EMAIL)
    assert admin_user.check_password(LOCAL_ADMIN_PASSWORD)

    store = Store.objects.create(
        name="B.A.D.R.",
        street_number="0000",
        street_name="rue Exemple",
        city="Montreal",
        postal_code="H0H 0H0",
        phone="514-555-0100",
        email="badr-store@example.test",
        opening_hours={"mon": [["09:00", "17:00"]]},
        is_badr=True,
    )
    store_admin = admin.site._registry[Store]
    change_url = reverse("admin:stores_store_change", args=[store.pk])
    request = RequestFactory().post(change_url)
    request.user = admin_user

    assert store_admin.has_view_permission(request, store)
    assert store_admin.has_change_permission(request, store)
    form_class = store_admin.get_form(request, obj=store)
    form = form_class(
        {
            "name": store.name,
            "street_number": store.street_number,
            "street_name": store.street_name,
            "unit": "",
            "city": store.city,
            "postal_code": store.postal_code,
            "phone": "514-555-0199",
            "email": store.email,
            "opening_hours": '{"mon": [["09:00", "17:00"]]}',
            "pickup_instructions": "",
            "is_badr": "on",
            "is_active": "on",
        },
        instance=store,
    )
    assert form.is_valid(), form.errors.as_json()
    store_admin.save_model(request, form.save(commit=False), form, change=True)

    store.refresh_from_db()
    assert store.phone == "514-555-0199"


@pytest.mark.django_db
def test_non_admins_have_no_store_admin_permissions() -> None:
    """Refuse anonymous and ordinary users through Django admin permissions."""
    store_admin = admin.site._registry[Store]
    request = RequestFactory().get("/admin/stores/store/")
    request.user = AnonymousUser()
    assert not store_admin.has_view_permission(request)
    assert not store_admin.has_change_permission(request)

    request.user = get_user_model()._default_manager.create_user(
        username="non-admin@example.test", password="local-test-password"
    )
    assert not store_admin.has_view_permission(request)
    assert not store_admin.has_change_permission(request)
