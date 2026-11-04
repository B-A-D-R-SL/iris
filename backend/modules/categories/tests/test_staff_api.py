# AI contribution: 50% or more AI-generated
"""Admin category management (US-35, T-05.35.2): API, services and rules."""

from copy import deepcopy
from datetime import timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.categories.domain.rules import (
    DefaultValueOutOfRange,
    validate_default_value,
)
from modules.categories.models import Category
from modules.categories.tests.factories import CategoryFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db

LIST = reverse("staff-categories")
MAX_CENTS = DEFAULT_RULE_VALUES["listing_posting"]["estimated_value_max_cents"]


def _user(role: str, **extra: Any) -> Any:
    if role.startswith("store_"):
        extra.setdefault("store", StoreFactory())
    return UserFactory(role=role, **extra)


def _client(user: Any = None, language: str = "fr") -> APIClient:
    client = APIClient(HTTP_ACCEPT_LANGUAGE=language)
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _detail(code: str) -> str:
    return reverse("staff-category-detail", kwargs={"code": code})


@pytest.fixture
def admin() -> Any:
    return _user("admin")


@pytest.fixture
def rules(admin: Any) -> None:
    """The value limit lives in the listing_posting rule setting."""
    publish(
        "listing_posting",
        deepcopy(DEFAULT_RULE_VALUES["listing_posting"]),
        admin,
        effective_from=timezone.now() - timedelta(days=1),
    )


NEW = {
    "code": "pet_food",
    "name_fr": "Nourriture pour animaux",
    "name_en": "Pet food",
    "is_food": False,
    "default_value_cents": 600,
}


# ---------------------------------------------------------------- AC1: the six fields


def test_admin_adds_a_category_with_every_field(admin: Any, rules: None) -> None:
    response = _client(admin).post(LIST, NEW, format="json")

    assert response.status_code == 201, response.data
    assert response.data == {**NEW, "is_active": True}
    saved = Category.objects.get(code="pet_food")
    assert (saved.name_fr, saved.name_en, saved.is_food) == (
        "Nourriture pour animaux",
        "Pet food",
        False,
    )


def test_admin_lists_active_and_inactive_categories(admin: Any) -> None:
    CategoryFactory(code="bakery")
    CategoryFactory(code="school_supplies", is_active=False)

    response = _client(admin).get(LIST)

    assert response.status_code == 200
    assert [(c["code"], c["is_active"]) for c in response.data] == [
        ("bakery", True),
        ("school_supplies", False),
    ]


def test_admin_renames_and_changes_a_category(admin: Any, rules: None) -> None:
    CategoryFactory(code="pet_food", name_en="Pet food", is_food=False)

    response = _client(admin).patch(
        _detail("pet_food"),
        {
            "name_en": "Pet food and supplies",
            "is_food": True,
            "default_value_cents": 900,
        },
        format="json",
    )

    assert response.status_code == 200, response.data
    saved = Category.objects.get(code="pet_food")
    assert (saved.name_en, saved.is_food, saved.default_value_cents) == (
        "Pet food and supplies",
        True,
        900,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "Pet Food"),
        ("code", "9lives"),
        ("code", "x" * 65),
        ("name_fr", ""),
        ("name_en", "   "),
        ("name_en", "x" * 151),
        ("default_value_cents", -1),
        ("default_value_cents", "abc"),
    ],
)
def test_invalid_fields_are_refused(
    admin: Any, rules: None, field: str, value: Any
) -> None:
    response = _client(admin).post(LIST, {**NEW, field: value}, format="json")

    assert response.status_code == 400
    assert field in response.data["fields"]
    assert not Category.objects.filter(code=NEW["code"]).exists()


def test_default_value_follows_the_listing_value_limit(admin: Any, rules: None) -> None:
    at_limit = _client(admin).post(
        LIST, {**NEW, "default_value_cents": MAX_CENTS}, format="json"
    )
    over = _client(admin).post(
        LIST,
        {**NEW, "code": "too_much", "default_value_cents": MAX_CENTS + 1},
        format="json",
    )

    assert at_limit.status_code == 201
    assert over.status_code == 400
    assert "default_value_cents" in over.data["fields"]


def test_unchanged_value_is_not_checked_against_a_lower_limit(admin: Any) -> None:
    CategoryFactory(code="pet_food", default_value_cents=50_000)
    lower = deepcopy(DEFAULT_RULE_VALUES["listing_posting"])
    lower["estimated_value_max_cents"] = 10_000
    publish(
        "listing_posting",
        lower,
        admin,
        effective_from=timezone.now() - timedelta(days=1),
    )

    same = _client(admin).patch(
        _detail("pet_food"),
        {"name_en": "Pet supplies", "default_value_cents": 50_000},
        format="json",
    )
    changed = _client(admin).patch(
        _detail("pet_food"), {"default_value_cents": 40_000}, format="json"
    )

    assert same.status_code == 200, same.data
    assert Category.objects.get(code="pet_food").name_en == "Pet supplies"
    assert changed.status_code == 400
    assert "default_value_cents" in changed.data["fields"]


def test_renaming_with_the_same_value_does_not_need_the_rules(admin: Any) -> None:
    CategoryFactory(code="pet_food", default_value_cents=600)

    response = _client(admin).patch(
        _detail("pet_food"),
        {"name_en": "Pet supplies", "default_value_cents": 600},
        format="json",
    )

    assert response.status_code == 200, response.data


def test_a_duplicate_code_is_refused(admin: Any, rules: None) -> None:
    CategoryFactory(code="pet_food")

    response = _client(admin).post(LIST, NEW, format="json")

    assert response.status_code == 400
    assert response.data["fields"]["code"] == ["Ce code de catégorie existe déjà."]


def test_the_code_cannot_change(admin: Any) -> None:
    CategoryFactory(code="pet_food")

    response = _client(admin).patch(
        _detail("pet_food"), {"code": "pets"}, format="json"
    )

    assert response.status_code == 400
    assert response.data["fields"]["code"] == [
        "Le code d'une catégorie ne peut pas être modifié."
    ]
    assert Category.objects.filter(code="pet_food").exists()


def test_unknown_fields_are_refused(admin: Any, rules: None) -> None:
    response = _client(admin).post(LIST, {**NEW, "id": "x"}, format="json")

    assert response.status_code == 400
    assert "id" in response.data["fields"]


def test_errors_come_in_english_on_request(admin: Any) -> None:
    CategoryFactory(code="pet_food")

    response = _client(admin, language="en").patch(
        _detail("pet_food"), {"code": "pets"}, format="json"
    )

    assert response.data["fields"]["code"] == ["A category code cannot be changed."]
    assert response.data["message"] == "Check the highlighted fields."


def test_saving_needs_the_listing_rules(admin: Any) -> None:
    response = _client(admin).post(LIST, NEW, format="json")

    assert response.status_code == 503
    assert response.data["code"] == "rules_unavailable"
    assert not Category.objects.filter(code="pet_food").exists()


# ---------------------------------------------------------------- AC2: deactivate, never delete


def test_there_is_no_delete(admin: Any) -> None:
    CategoryFactory(code="bakery")

    response = _client(admin).delete(_detail("bakery"))

    assert response.status_code == 405
    assert Category.objects.filter(code="bakery").exists()


def test_deactivated_category_is_hidden_from_the_public_list(admin: Any) -> None:
    CategoryFactory(code="bakery")

    response = _client(admin).patch(
        _detail("bakery"), {"is_active": False}, format="json"
    )
    public = _client().get(reverse("categories-list"))

    assert response.status_code == 200
    assert response.data["is_active"] is False
    assert Category.objects.filter(code="bakery").exists()
    assert "bakery" not in [c["code"] for c in public.json()]


def test_reactivated_category_is_back_in_the_public_list(admin: Any) -> None:
    CategoryFactory(code="bakery", is_active=False)

    _client(admin).patch(_detail("bakery"), {"is_active": True}, format="json")
    public = _client().get(reverse("categories-list"))

    assert "bakery" in [c["code"] for c in public.json()]


def test_unknown_code_is_not_found(admin: Any) -> None:
    response = _client(admin).patch(_detail("nope"), {"name_en": "X"}, format="json")

    assert response.status_code == 404


# ---------------------------------------------------------------- every role


@pytest.mark.parametrize(
    "role", ["intake_worker", "store_staff", "store_manager", "beneficiary"]
)
def test_other_roles_are_refused(role: str, rules: None) -> None:
    CategoryFactory(code="bakery")
    client = _client(_user(role))

    assert client.get(LIST).status_code == 403
    assert client.post(LIST, NEW, format="json").status_code == 403
    assert (
        client.patch(_detail("bakery"), {"is_active": False}, format="json").status_code
        == 403
    )
    assert Category.objects.get(code="bakery").is_active is True


def test_signed_out_visitors_are_refused() -> None:
    CategoryFactory(code="bakery")

    # 401: not signed in (the project's session authentication), not a role refusal.
    assert _client().get(LIST).status_code == 401
    assert _client().post(LIST, NEW, format="json").status_code == 401


def test_inactive_admin_is_refused(rules: None) -> None:
    client = _client(_user("admin", is_active=False))

    assert client.get(LIST).status_code == 403


# ---------------------------------------------------------------- pure rule


@pytest.mark.parametrize(
    ("value", "ok"),
    [(0, True), (500, True), (100_000, True), (100_001, False), (-1, False)],
)
def test_default_value_rule(value: int, ok: bool) -> None:
    if ok:
        validate_default_value(value, max_cents=100_000)
    else:
        with pytest.raises(DefaultValueOutOfRange):
            validate_default_value(value, max_cents=100_000)


def test_default_value_is_required_when_adding(admin: Any, rules: None) -> None:
    body = {key: value for key, value in NEW.items() if key != "default_value_cents"}

    response = _client(admin).post(LIST, body, format="json")

    assert response.status_code == 400
    assert "default_value_cents" in response.data["fields"]


# ---------------------------------------------------------------- main path (API + database)


def test_main_path_add_rename_deactivate_reactivate(admin: Any, rules: None) -> None:
    client = _client(admin, language="en")

    created = client.post(LIST, NEW, format="json")
    renamed = client.patch(
        _detail("pet_food"), {"name_en": "Pet supplies"}, format="json"
    )
    deactivated = client.patch(_detail("pet_food"), {"is_active": False}, format="json")
    admin_list = client.get(LIST)
    public_list = _client().get(reverse("categories-list"))
    reactivated = client.patch(_detail("pet_food"), {"is_active": True}, format="json")

    assert [created.status_code, renamed.status_code, deactivated.status_code] == [
        201,
        200,
        200,
    ]
    assert {"code": "pet_food", "is_active": False}.items() <= next(
        c for c in admin_list.data if c["code"] == "pet_food"
    ).items()
    assert "pet_food" not in [c["code"] for c in public_list.json()]
    assert reactivated.data["is_active"] is True
    saved = Category.objects.get(code="pet_food")
    assert (saved.name_en, saved.name_fr, saved.is_active) == (
        "Pet supplies",
        "Nourriture pour animaux",
        True,
    )
