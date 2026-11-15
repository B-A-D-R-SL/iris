# AI contribution: 50% or more AI-generated
"""FIX-01: posting outcomes survive JSON privacy filtering and transaction rollback."""

import json
import logging
import sys
from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.urls import reverse
from rest_framework.test import APIClient

from adapters.photo_types import PhotoStorageError
from iris.observability import JsonLogFormatter
from modules.listings import services
from modules.listings.domain.posting import Refusal, SafetyRulesInvalid
from modules.listings.models import Listing
from modules.listings.tests.fake_photo_store import MemoryPhotoStore
from modules.listings.tests.test_photo_upload import upload
from modules.listings.tests.test_post_listing_api import payload

PRIVATE_MARKERS = (
    "private@example.test",
    "private-title",
    "private-description",
    "storage-secret",
    "private-name",
    "private-filename",
)
PRIVATE = " ".join(PRIVATE_MARKERS)
MESSAGES = {
    "en": "Posting is temporarily unavailable.",
    "fr": "La publication est temporairement indisponible.",
}


def events(caplog: pytest.LogCaptureFixture, event: str) -> list[dict[str, Any]]:
    """Check both raw records and the JSON that operators actually receive."""
    records = [record for record in caplog.records if record.name == "iris.listings"]
    encoded = [JsonLogFormatter().format(record) for record in records]
    assert all(marker not in caplog.text for marker in PRIVATE_MARKERS)
    assert all(marker not in line for line in encoded for marker in PRIVATE_MARKERS)
    assert all(record.exc_info is None for record in records)
    return [json.loads(line) for line in encoded if json.loads(line)["event"] == event]


def test_publication_event_has_ids_only_after_commit(
    posting_case, caplog, django_capture_on_commit_callbacks
):
    """A successful response emits safe IDs only when its write commits."""
    case = posting_case
    caplog.set_level(logging.INFO, logger="iris.listings")
    data = replace(case.data, title="private-title", description=PRIVATE)
    with django_capture_on_commit_callbacks(execute=True):
        listing = services.post_listing(case.store.pk, case.user, data)
        assert events(caplog, "listing_published") == []
    [event] = events(caplog, "listing_published")
    assert event["listing_id"] == str(listing.pk)
    assert event["store_id"] == str(case.store.pk)
    assert set(event) == {
        "timestamp",
        "level",
        "logger",
        "event",
        "listing_id",
        "store_id",
    }
    assert event["level"] == "INFO"
    assert "private-title" not in caplog.text


def test_outer_transaction_rollback_emits_no_publication(
    posting_case, caplog, django_capture_on_commit_callbacks
):
    """A later failure in a surrounding workflow cannot report publication."""
    case = posting_case
    caplog.set_level(logging.INFO, logger="iris.listings")
    with (
        django_capture_on_commit_callbacks(execute=True),
        pytest.raises(RuntimeError, match="rollback"),
        transaction.atomic(),
    ):
        services.post_listing(case.store.pk, case.user, case.data)
        raise RuntimeError("rollback")
    assert not Listing.objects.exists()
    assert events(caplog, "listing_published") == []


@pytest.mark.parametrize("code", list(services.MESSAGES))
def test_safety_refusal_reason_survives_formatter_without_input(
    posting_case, caplog, code
):
    """Every domain refusal code is registered, without field values or params."""
    case = posting_case
    checker = Mock(return_value=[Refusal("title", code, {"date": case.now.date()})])
    data = replace(case.data, title="private-title", description=PRIVATE)
    with pytest.raises(ValidationError):
        services.post_listing(case.store.pk, case.user, data, safety_check=checker)
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == code
    assert event["level"] == "WARNING"
    assert set(event) == {"timestamp", "level", "logger", "event", "reason"}
    assert not Listing.objects.exists()


def test_validation_logs_all_distinct_reasons_and_keeps_field_errors(
    posting_case, caplog
):
    """Validation still accumulates multiple field errors before calling safety."""
    case = posting_case
    checker = Mock()
    data = replace(case.data, quantity=0, safe_and_allowed=False, description=PRIVATE)
    with pytest.raises(ValidationError) as caught:
        services.post_listing(case.store.pk, case.user, data, safety_check=checker)
    assert set(caught.value.message_dict) == {"quantity", "safe_and_allowed"}
    assert {event["reason"] for event in events(caplog, "listing_post_refused")} == {
        "quantity_range",
        "confirmation_required",
    }
    checker.assert_not_called()


def test_unknown_model_code_is_replaced_with_static_reason(
    posting_case, caplog, monkeypatch
):
    """Untrusted model messages/codes never become logging fields."""
    monkeypatch.setattr(
        Listing, "full_clean", Mock(side_effect=ValidationError(PRIVATE, code=PRIVATE))
    )
    case = posting_case
    with pytest.raises(ValidationError):
        services.post_listing(case.store.pk, case.user, case.data)
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == "listing_validation_failed"


def test_wrong_store_refusal_has_no_user_or_store_details(posting_case, caplog):
    """Service ownership checks keep working and emit only the reason."""
    case = posting_case
    with pytest.raises(PermissionDenied):
        services.post_listing(uuid4(), case.user, case.data)
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == "store_access_denied"
    assert "store_id" not in event


def break_dependency(
    reason: str, monkeypatch: pytest.MonkeyPatch, settings: Any
) -> bool:
    """Inject a failure at its real boundary; return whether a photo is needed."""
    if reason == "listing_rules_missing":
        monkeypatch.setattr(
            services.rule_queries, "active", lambda *args, **kwargs: None
        )
    elif reason == "posting_rules_invalid":
        monkeypatch.setattr(
            services.rule_queries,
            "active",
            lambda *args, **kwargs: SimpleNamespace(values={}),
        )
    elif reason == "safety_rules_invalid":
        monkeypatch.setattr(
            services,
            "_safety_checker",
            lambda: Mock(side_effect=SafetyRulesInvalid(PRIVATE)),
        )
    elif reason == "safety_checker_missing":
        monkeypatch.setitem(sys.modules, "modules.listings.domain.safety", None)
    elif reason == "safety_contract_invalid":
        monkeypatch.setattr(
            services, "_safety_checker", lambda: Mock(return_value=[PRIVATE])
        )
    elif reason == "photo_store_unconfigured":
        settings.LISTING_PHOTO_STORE_BACKEND = ""
    elif reason == "photo_store_failed":
        store = Mock()
        store.put_image.side_effect = PhotoStorageError(PRIVATE)
        monkeypatch.setattr(services, "_photo_store", lambda: store)
    elif reason == "photo_factory_failed":
        settings.LISTING_PHOTO_STORE_BACKEND = "configured.for.test"
        monkeypatch.setattr(
            services, "load_store", Mock(side_effect=PhotoStorageError(PRIVATE))
        )
    return reason.startswith("photo_")


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize(
    "reason",
    [
        "listing_rules_missing",
        "posting_rules_invalid",
        "safety_rules_invalid",
        "safety_checker_missing",
        "safety_contract_invalid",
        "photo_store_unconfigured",
        "photo_store_failed",
        "photo_factory_failed",
    ],
)
def test_all_posting_dependencies_have_generic_503_and_safe_reason(
    posting_case, monkeypatch, settings, caplog, reason, language
):
    """Actual API responses share one translation; diagnostics keep their code."""
    needs_photo = break_dependency(reason, monkeypatch, settings)
    client = APIClient(HTTP_ACCEPT_LANGUAGE=language)
    client.force_authenticate(user=posting_case.user)
    data = {**payload(posting_case), "title": "private-title", "description": PRIVATE}
    if needs_photo:
        data["photo"] = upload()
    response = client.post(reverse("store-listing-create"), data, format="multipart")
    assert response.status_code == 503
    assert response.json() == {
        "code": "posting_unavailable",
        "message": MESSAGES[language],
        "fields": {},
    }
    expected = "photo_store_failed" if reason == "photo_factory_failed" else reason
    [event] = events(caplog, "listing_posting_unavailable")
    assert event["reason"] == expected
    assert event["level"] == "ERROR"
    if expected == "photo_store_failed":
        [failure] = events(caplog, "listing_photo_store_failed")
        assert failure["exc_type"] == "PhotoStorageError"
        assert set(failure) <= {
            "timestamp",
            "level",
            "logger",
            "event",
            "request_id",
            "exc_type",
        }
    assert not Listing.objects.exists()
    assert events(caplog, "listing_published") == []


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("reason", ["listing_rules_missing", "safety_rules_invalid"])
def test_categories_uses_same_generic_503_and_safe_reason(
    posting_case, monkeypatch, caplog, language, reason
):
    """Opening the posting form exposes no rule/configuration details either."""
    if reason == "listing_rules_missing":
        monkeypatch.setattr(
            services.rule_queries, "active", lambda *args, **kwargs: None
        )
    else:
        monkeypatch.setattr(
            services.rule_queries,
            "active",
            lambda *args, **kwargs: SimpleNamespace(values={}),
        )
    client = APIClient(HTTP_ACCEPT_LANGUAGE=language)
    client.force_authenticate(user=posting_case.user)
    response = client.get(reverse("store-listing-categories"))
    assert response.status_code == 503
    assert response.json()["message"] == MESSAGES[language]
    [event] = events(caplog, "listing_posting_unavailable")
    assert event["reason"] == reason


@pytest.mark.parametrize(
    ("logger", "event", "valid"),
    [
        ("iris.listings", "listing_published", True),
        ("iris.listings", "listing_post_refused", False),
        ("iris.other", "listing_published", False),
    ],
)
def test_formatter_scopes_listing_ids_to_publication(logger, event, valid):
    """Opaque IDs are allowed only on the intended logger/event pair."""
    listing_id, store_id = uuid4(), uuid4()
    record = logging.makeLogRecord(
        {
            "name": logger,
            "event": event,
            "listing_id": listing_id,
            "store_id": store_id,
            "msg": PRIVATE,
            "title": PRIVATE,
            "description": PRIVATE,
            "user_id": uuid4(),
        }
    )
    encoded = JsonLogFormatter().format(record)
    result = json.loads(encoded)
    assert (result.get("listing_id") == str(listing_id)) is valid
    assert (result.get("store_id") == str(store_id)) is valid
    assert all(marker not in encoded for marker in PRIVATE_MARKERS)
    assert "user_id" not in result


@pytest.mark.parametrize("value", [PRIVATE, "not-a-uuid", True, 42, None])
def test_formatter_discards_invalid_listing_ids(value):
    """Free text and non-UUID identifiers cannot enter publication JSON."""
    record = logging.makeLogRecord(
        {
            "name": "iris.listings",
            "event": "listing_published",
            "listing_id": value,
            "store_id": value,
        }
    )
    result = json.loads(JsonLogFormatter().format(record))
    assert "listing_id" not in result
    assert "store_id" not in result


@pytest.mark.parametrize(
    ("changes", "status", "reason"),
    [
        ({"quantity": "invalid"}, 400, "listing_validation_failed"),
        ({"unknown_field": PRIVATE}, 400, "listing_validation_failed"),
        ({"store": str(uuid4())}, 403, "store_access_denied"),
    ],
)
def test_api_refusals_before_service_are_logged(
    posting_case, caplog, changes, status, reason
):
    """Serializer rejection and explicit store overrides also produce safe events."""
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    response = client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), **changes},
        format="json",
    )
    assert response.status_code == status
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == reason
    assert not Listing.objects.exists()


@pytest.mark.parametrize("reason", ["photo_type", "photo_size", "photo_invalid"])
def test_photo_validation_logs_reason_and_preserves_400(
    posting_case, caplog, monkeypatch, reason
):
    """Bad uploads remain field errors and never become availability failures."""
    content, content_type = b"not an image", "text/plain"
    if reason == "photo_size":
        content, content_type = b"x" * (5 * 1024 * 1024 + 1), "image/jpeg"
    elif reason == "photo_invalid":
        content, content_type = (
            bytes.fromhex("89504e470d0a1a0a") + b"corrupt",
            "image/png",
        )
    monkeypatch.setattr(services, "_photo_store", lambda: MemoryPhotoStore())
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    photo = SimpleUploadedFile("private-filename", content, content_type=content_type)
    response = client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), "photo": photo},
        format="multipart",
    )
    assert response.status_code == 400
    assert "photo" in response.json()["fields"]
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == reason
    assert "private-filename" not in caplog.text
    assert events(caplog, "listing_posting_unavailable") == []
    assert not Listing.objects.exists()


def test_inactive_category_has_registered_refusal_reason(posting_case, caplog):
    """Invalid category lookup preserves its field error and safe diagnosis."""
    case = posting_case
    with pytest.raises(ValidationError) as caught:
        services.post_listing(
            case.store.pk, case.user, replace(case.data, category="missing")
        )
    assert "category" in caught.value.message_dict
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == "category_inactive"


@pytest.mark.parametrize(
    "account",
    [
        "beneficiary",
        "intake_worker",
        "admin",
        "inactive",
        "no_store",
        "anonymous",
    ],
)
def test_permission_refusals_emit_one_safe_event_before_service(
    posting_case, monkeypatch, caplog, account
):
    """DRF authorization failures produce a refusal without invoking posting."""
    case = posting_case
    client = APIClient()
    if account != "anonymous":
        if account == "inactive":
            case.user.is_active = False
        elif account == "no_store":
            case.user.store_id = None
        else:
            case.user.role = account
        client.force_authenticate(user=case.user)
    post = Mock()
    monkeypatch.setattr(services, "post_listing", post)
    response = client.post(
        reverse("store-listing-create"), payload(case), format="json"
    )
    assert response.status_code == 403
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == "store_access_denied"
    post.assert_not_called()
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    ("content_type", "body", "status"),
    [
        ("application/json", '{"private-name":', 400),
        ("text/plain", PRIVATE, 415),
    ],
)
def test_body_parser_refusals_emit_one_safe_event_before_service(
    posting_case, monkeypatch, caplog, content_type, body, status
):
    """Malformed JSON and unsupported bodies are diagnosed without logging content."""
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    post = Mock()
    monkeypatch.setattr(services, "post_listing", post)
    response = client.post(
        reverse("store-listing-create"), body, content_type=content_type
    )
    assert response.status_code == status
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == "listing_validation_failed"
    post.assert_not_called()
    assert not Listing.objects.exists()


def test_api_service_validation_retains_its_reason_without_duplicate_event(
    posting_case, caplog
):
    """The API must not add a generic event to a service's specific refusal."""
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    response = client.post(
        reverse("store-listing-create"),
        {**payload(posting_case), "quantity": 0},
        format="json",
    )
    assert response.status_code == 400
    assert "quantity" in response.json()["fields"]
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == "quantity_range"
    assert not Listing.objects.exists()


def test_api_service_permission_failure_is_not_logged_twice(posting_case, caplog):
    """An inactive store is refused inside the service and keeps exactly one event."""
    case = posting_case
    case.store.is_active = False
    case.store.save(update_fields=["is_active"])
    client = APIClient()
    client.force_authenticate(user=case.user)
    response = client.post(
        reverse("store-listing-create"), payload(case), format="json"
    )
    assert response.status_code == 403
    [event] = events(caplog, "listing_post_refused")
    assert event["reason"] == "store_access_denied"
    assert not Listing.objects.exists()


@pytest.mark.parametrize(
    "endpoint", ["store-listing-create", "store-listing-categories"]
)
def test_get_permission_failure_is_not_logged_as_a_post(posting_case, caplog, endpoint):
    """Only publication attempts receive the listing_post_refused event."""
    posting_case.user.role = "beneficiary"
    client = APIClient()
    client.force_authenticate(user=posting_case.user)
    response = client.get(reverse(endpoint))
    assert response.status_code == 403
    assert events(caplog, "listing_post_refused") == []
