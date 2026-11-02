# AI contribution: 50% or more AI-generated
"""Real PostgreSQL writes; only unfinished safety/storage integrations are fakes."""

import sys
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from modules.listings import services
from modules.listings.domain.posting import Refusal
from modules.listings.models import Listing
from modules.listings.tests.factories import create_staff_user
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.models import RuleSetVersion
from modules.rules.services import publish

PNG_CONTENT = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
    "0000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082"
)
JPEG_CONTENT = b"\xff\xd8\xff\xe0test-image"


def test_us33_posts_with_server_owned_fields_and_zero_reservations(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    checker = Mock(return_value=[])
    listing = services.post_listing(
        case.store.pk,
        case.user,
        replace(case.data, title="  Bread  "),
        safety_check=checker,
    )
    listing.refresh_from_db()
    assert listing.title == "Bread"
    assert listing.store_id == case.store.pk
    assert listing.category_id == case.category.pk
    assert listing.quantity_total == 5
    assert listing.quantity_reserved == 0
    assert listing.status == "published"
    assert listing.created_by_id == case.user.pk
    assert listing.safe_confirmed_by_id == case.user.pk
    assert listing.safe_confirmed_at == listing.published_at == case.now
    assert listing.estimated_value_cents is None
    checker.assert_called_once()
    payload, category, rules = checker.call_args.args
    assert payload["best_before"] == case.data.best_before
    assert category["is_food"] is True
    assert category["code"] == case.category.code
    assert rules == DEFAULT_RULE_VALUES["listing_safety"]


@pytest.mark.parametrize("role", ["store_staff", "store_manager"])
def test_us33_allows_store_posting_roles(
    posting_case: SimpleNamespace, role: str
) -> None:
    case = posting_case
    case.user.role = role
    services.post_listing(
        case.store.pk, case.user, case.data, safety_check=Mock(return_value=[])
    )
    assert Listing.objects.count() == 1


@pytest.mark.parametrize(
    "role", ["beneficiary", "intake_worker", "admin", "unknown", None]
)
def test_us33_refuses_other_roles(
    posting_case: SimpleNamespace, role: str | None
) -> None:
    case = posting_case
    case.user.role = role
    with pytest.raises(PermissionDenied):
        services.post_listing(case.store.pk, case.user, case.data)
    assert not Listing.objects.exists()


def test_us33_default_user_does_not_gain_posting_rights(
    posting_case: SimpleNamespace,
) -> None:
    ordinary_user: Any = create_staff_user()
    ordinary_user.is_staff = True
    ordinary_user.is_superuser = True
    with pytest.raises(PermissionDenied):
        services.post_listing(posting_case.store.pk, ordinary_user, posting_case.data)
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    "change",
    ["wrong_store", "no_store", "inactive_user", "inactive_store", "missing_store"],
)
def test_us33_refuses_invalid_store_access(
    posting_case: SimpleNamespace, change: str
) -> None:
    case = posting_case
    store_id = case.store.pk
    if change == "wrong_store":
        store_id = uuid4()
    elif change == "no_store":
        case.user.store_id = None
    elif change == "inactive_user":
        case.user.is_active = False
    elif change == "inactive_store":
        case.store.is_active = False
        case.store.save()
    else:
        case.user.store_id = store_id = uuid4()
    with pytest.raises(PermissionDenied):
        services.post_listing(store_id, case.user, case.data)
    assert not Listing.objects.exists()


@pytest.mark.parametrize("missing", [False, True])
def test_us33_requires_an_existing_active_category(
    posting_case: SimpleNamespace, missing: bool
) -> None:
    case = posting_case
    data = case.data
    if missing:
        data = replace(data, category="no_such_category")
    else:
        case.category.is_active = False
        case.category.save()
    with pytest.raises(ValidationError) as caught:
        services.post_listing(case.store.pk, case.user, data)
    assert "category" in caught.value.message_dict
    assert not Listing.objects.exists()


def test_us33_refuses_invalid_data_before_calling_safety(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    checker = Mock(return_value=[])
    with pytest.raises(ValidationError) as caught:
        services.post_listing(
            case.store.pk,
            case.user,
            replace(case.data, quantity=0, safe_and_allowed=False),
            safety_check=checker,
        )
    assert set(caught.value.message_dict) == {"quantity", "safe_and_allowed"}
    checker.assert_not_called()
    assert not Listing.objects.exists()


def test_us33_uses_latest_effective_rule_versions(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    limits = {**DEFAULT_RULE_VALUES["listing_posting"], "quantity_max": 2}
    publish("listing_posting", limits, case.user, effective_from=case.now)
    future = deepcopy(DEFAULT_RULE_VALUES["listing_posting"])
    publish(
        "listing_posting",
        future,
        case.user,
        effective_from=case.now + timedelta(days=1),
    )
    with pytest.raises(ValidationError) as caught:
        services.post_listing(
            case.store.pk, case.user, case.data, safety_check=Mock(return_value=[])
        )
    assert "quantity" in caught.value.message_dict
    assert not Listing.objects.exists()


def test_us33_never_publishes_when_safety_dependency_is_missing(
    posting_case: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = posting_case
    monkeypatch.setitem(sys.modules, "modules.listings.domain.safety", None)
    with pytest.raises(services.PostingUnavailable, match="safety"):
        services.post_listing(case.store.pk, case.user, case.data)
    assert not Listing.objects.exists()


@pytest.mark.parametrize("missing", ["listing_posting", "listing_safety"])
def test_us33_requires_effective_rule_versions(
    posting_case: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    case = posting_case
    original_active = services.rule_queries.active

    def active(rule_type: str, **kwargs: Any) -> Any:
        return None if rule_type == missing else original_active(rule_type, **kwargs)

    monkeypatch.setattr(services.rule_queries, "active", active)
    checker = Mock(return_value=[])
    with pytest.raises(services.PostingUnavailable, match="seeded"):
        services.post_listing(case.store.pk, case.user, case.data, safety_check=checker)
    checker.assert_not_called()
    assert not Listing.objects.exists()


@pytest.mark.parametrize("configuration_error", ["missing_key", "unexpected_key"])
def test_us33_refuses_malformed_posting_rule_configuration(
    posting_case: SimpleNamespace, configuration_error: str
) -> None:
    case = posting_case
    values = deepcopy(DEFAULT_RULE_VALUES["listing_posting"])
    if configuration_error == "missing_key":
        values.pop("quantity_max")
    else:
        values["unexpected_limit"] = 1
    # Simulate an incompatible stored version, bypassing publish's validation.
    RuleSetVersion.objects.create(
        rule_type="listing_posting",
        version=2,
        values=values,
        effective_from=case.now,
        created_by=case.user,
    )
    checker = Mock(return_value=[])
    with pytest.raises(services.PostingUnavailable, match="rules need configuration"):
        services.post_listing(case.store.pk, case.user, case.data, safety_check=checker)
    checker.assert_not_called()
    assert not Listing.objects.exists()


def test_us33_loads_checker_through_contract_without_adding_ryans_file(
    posting_case: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = posting_case
    module = ModuleType("modules.listings.domain.safety")
    checker = Mock(return_value=[])
    module.check = checker  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, module.__name__, module)
    services.post_listing(case.store.pk, case.user, case.data)
    checker.assert_called_once()
    assert Listing.objects.count() == 1


@pytest.mark.parametrize("field", ["best_before", "category"])
def test_us33_preserves_safety_refusals(
    posting_case: SimpleNamespace, field: str
) -> None:
    case = posting_case
    checker = Mock(return_value=[Refusal(field, "unsafe_listing")])
    with pytest.raises(ValidationError) as caught:
        services.post_listing(case.store.pk, case.user, case.data, safety_check=checker)
    assert field in caught.value.message_dict
    assert not Listing.objects.exists()


def test_us33_rejects_unknown_safety_contract(posting_case: SimpleNamespace) -> None:
    case = posting_case
    with pytest.raises(services.PostingUnavailable):
        services.post_listing(
            case.store.pk,
            case.user,
            case.data,
            safety_check=Mock(return_value=["not the agreed contract"]),
        )
    assert not Listing.objects.exists()


def test_us33_storage_is_used_only_after_validation(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    store = Mock()
    with pytest.raises(ValidationError):
        services.post_listing(
            case.store.pk,
            case.user,
            replace(case.data, safe_and_allowed=False),
            photo=SimpleUploadedFile(
                "photo.png", PNG_CONTENT, content_type="image/png"
            ),
            safety_check=Mock(return_value=[]),
            file_store=store,
        )
    store.put_image.assert_not_called()


@pytest.mark.parametrize(
    ("content_type", "content"),
    [("image/png", PNG_CONTENT), ("image/jpeg", JPEG_CONTENT)],
)
def test_us33_passes_photo_bounds_to_the_storage_adapter(
    posting_case: SimpleNamespace, content_type: str, content: bytes
) -> None:
    case = posting_case
    store = Mock()
    store.put_image.return_value = "photos/test-reference"
    listing = services.post_listing(
        case.store.pk,
        case.user,
        case.data,
        photo=SimpleUploadedFile("photo", content, content_type=content_type),
        safety_check=Mock(return_value=[]),
        file_store=store,
    )
    store.put_image.assert_called_once_with(content, max_dimension=1280)
    store.delete.assert_not_called()
    assert listing.photo_ref == "photos/test-reference"


@pytest.mark.parametrize("content_type", ["text/plain", "image/gif"])
def test_us33_refuses_unsupported_photo_types(
    posting_case: SimpleNamespace, content_type: str
) -> None:
    case = posting_case
    with pytest.raises(ValidationError) as caught:
        services.post_listing(
            case.store.pk,
            case.user,
            case.data,
            photo=SimpleUploadedFile("bad.txt", b"bad", content_type=content_type),
            safety_check=Mock(return_value=[]),
        )
    assert "photo" in caught.value.message_dict
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    ("content_type", "content"),
    [
        ("image/png", b"not an image"),
        ("image/jpeg", b"not an image"),
        ("image/png", JPEG_CONTENT),
        ("image/jpeg", PNG_CONTENT),
        ("image/png", b"\x89PNG"),
        ("image/jpeg", b"\xff\xd8"),
        ("image/png", b""),
    ],
)
def test_us33_refuses_photo_bytes_that_do_not_match_the_declared_type(
    posting_case: SimpleNamespace, content_type: str, content: bytes
) -> None:
    case = posting_case
    store = Mock()
    with pytest.raises(ValidationError) as caught:
        services.post_listing(
            case.store.pk,
            case.user,
            case.data,
            photo=SimpleUploadedFile("photo", content, content_type=content_type),
            safety_check=Mock(return_value=[]),
            file_store=store,
        )
    assert "photo" in caught.value.message_dict
    store.put_image.assert_not_called()
    assert not Listing.objects.exists()


def test_us33_refuses_oversized_photos(posting_case: SimpleNamespace) -> None:
    case = posting_case
    publish(
        "listing_posting",
        {**DEFAULT_RULE_VALUES["listing_posting"], "photo_max_bytes": 3},
        case.user,
        effective_from=case.now,
    )
    with pytest.raises(ValidationError) as caught:
        services.post_listing(
            case.store.pk,
            case.user,
            case.data,
            photo=SimpleUploadedFile(
                "photo.png", PNG_CONTENT, content_type="image/png"
            ),
            safety_check=Mock(return_value=[]),
        )
    assert "photo" in caught.value.message_dict
    assert not Listing.objects.exists()


def test_us33_missing_photo_storage_does_not_publish(
    posting_case: SimpleNamespace,
) -> None:
    case = posting_case
    with pytest.raises(services.PostingUnavailable, match="photo storage"):
        services.post_listing(
            case.store.pk,
            case.user,
            case.data,
            photo=SimpleUploadedFile(
                "photo.png", PNG_CONTENT, content_type="image/png"
            ),
            safety_check=Mock(return_value=[]),
        )
    assert not Listing.objects.exists()


def test_us33_removes_uploaded_photo_if_database_save_fails(
    posting_case: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = posting_case
    store = Mock()
    store.put_image.return_value = "photos/rollback"

    def failed_save(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database failure")

    monkeypatch.setattr(Listing, "save", failed_save)
    with pytest.raises(RuntimeError, match="database failure"):
        services.post_listing(
            case.store.pk,
            case.user,
            case.data,
            photo=SimpleUploadedFile(
                "photo.png", PNG_CONTENT, content_type="image/png"
            ),
            safety_check=Mock(return_value=[]),
            file_store=store,
        )
    store.delete.assert_called_once_with("photos/rollback")
    assert not Listing.objects.exists()
