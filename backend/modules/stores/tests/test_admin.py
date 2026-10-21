# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code
"""US-11 Django admin registration, form, and permission tests."""

from io import StringIO
from typing import cast

import pytest
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, RequestFactory, override_settings
from django.urls import reverse
from django.utils.translation import override

from modules.stores.models import Store
from modules.stores.tests.factories import StoreFactory

LOCAL_ADMIN_EMAIL = "admin@iris.local"
LOCAL_ADMIN_PASSWORD = "iris_local_admin_password"


@pytest.mark.parametrize(
    ("language", "app_name", "postal_error"),
    [
        ("fr", "Magasins", "Entrez un code postal canadien."),
        ("en", "Stores", "Enter a Canadian postal code."),
    ],
)
def test_store_admin_text_uses_current_language(
    language: str, app_name: str, postal_error: str
) -> None:
    """Translate the Store admin section and its postal-code validation error."""
    with override(language):
        assert str(apps.get_app_config("stores").verbose_name) == app_name
        field = Store._meta.get_field("postal_code")
        with pytest.raises(ValidationError) as error:
            field.run_validators("invalid")
        assert postal_error in error.value.messages


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("language", "expected_labels"),
    [
        (
            "fr",
            {
                "name": "Nom du magasin",
                "street_number": "Numéro civique",
                "street_name": "Rue",
                "unit": "App.",
                "city": "Ville",
                "postal_code": "Code postal",
                "phone": "Téléphone",
                "email": "Courriel",
                "opening_hours": "Heures d’ouverture",
                "pickup_instructions": "Instructions pour la cueillette",
                "is_active": "Actif",
            },
        ),
        (
            "en",
            {
                "name": "Store name",
                "street_number": "Street number",
                "street_name": "Street",
                "unit": "Apt.",
                "city": "City",
                "postal_code": "Postal code",
                "phone": "Phone number",
                "email": "Email address",
                "opening_hours": "Opening hours",
                "pickup_instructions": "Pickup instructions",
                "is_active": "Active",
            },
        ),
    ],
)
def test_store_admin_form_uses_translated_field_labels(
    client: Client, language: str, expected_labels: dict[str, str]
) -> None:
    """Show the approved Store form labels in both admin languages."""
    admin_user = get_user_model()._default_manager.create_superuser(
        username=LOCAL_ADMIN_EMAIL, password=LOCAL_ADMIN_PASSWORD
    )
    store = cast(Store, StoreFactory())
    client.force_login(admin_user)

    response = client.get(
        reverse("admin:stores_store_change", args=[store.pk]),
        headers={"Accept-Language": language},
    )

    assert response.status_code == 200
    form = response.context["adminform"].form
    for field_name, label in expected_labels.items():
        assert form.fields[field_name].label == label
    assert "is_badr" not in form.fields
    assert "is_badr" in response.context["adminform"].readonly_fields
    with override(language):
        badr_label = {"fr": "Magasin B.A.D.R.", "en": "B.A.D.R. store"}[language]
        assert str(Store._meta.get_field("is_badr").verbose_name) == badr_label
        assert badr_label in response.content.decode()
        assert (
            str(Store._meta.verbose_name) == {"fr": "Magasin", "en": "Store"}[language]
        )
        assert (
            str(Store._meta.verbose_name_plural)
            == {
                "fr": "Magasins",
                "en": "Stores",
            }[language]
        )
        assert str(Store._meta.get_field("id").verbose_name) == "ID"
        assert (
            str(Store._meta.get_field("created_at").verbose_name)
            == {
                "fr": "Créé le",
                "en": "Created at",
            }[language]
        )
        assert (
            str(Store._meta.get_field("updated_at").verbose_name)
            == {
                "fr": "Modifié le",
                "en": "Updated at",
            }[language]
        )


@pytest.mark.parametrize(
    ("accepted_language", "expected_language"),
    [("fr", "fr"), ("en", "en"), ("es", "fr")],
)
def test_admin_request_selects_supported_language(
    client: Client, accepted_language: str, expected_language: str
) -> None:
    """Select French or English for admin requests, defaulting to French."""
    response = client.get(
        "/admin/login/", headers={"Accept-Language": accepted_language}
    )
    assert response.wsgi_request.LANGUAGE_CODE == expected_language


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
        phone="+15145550100",
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
            "phone": "+15145550199",
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
    assert store.phone == "+15145550199"


@pytest.mark.django_db
def test_non_admins_have_no_store_admin_permissions() -> None:
    """Refuse anonymous, ordinary, and non-admin staff users."""
    store_admin = admin.site._registry[Store]
    request = RequestFactory().get("/admin/stores/store/")
    request.user = AnonymousUser()
    assert not store_admin.has_view_permission(request)
    assert not store_admin.has_change_permission(request)

    staff_user = get_user_model()._default_manager.create_user(
        username="staff@example.test",
        password="local-test-password",
        is_staff=True,
    )
    staff_user.user_permissions.set(
        Permission.objects.filter(codename__in=["view_store", "change_store"])
    )
    request.user = staff_user
    assert not store_admin.has_view_permission(request)
    assert not store_admin.has_change_permission(request)

    request.user = get_user_model()._default_manager.create_user(
        username="non-admin@example.test", password="local-test-password"
    )
    assert not store_admin.has_view_permission(request)
    assert not store_admin.has_change_permission(request)
