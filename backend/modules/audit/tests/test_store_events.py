# AI contribution: 50% or more AI-generated
"""Store audit events (US-14): update, deactivate and reactivate."""

from typing import Any
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from modules.accounts.tests.factories import UserFactory
from modules.audit import services
from modules.audit.models import AuditEvent


@pytest.fixture
def admin(db):
    return UserFactory(role="admin")


def _record(admin, action: str, metadata: dict[str, Any], target_type="store"):
    return services.record(admin, action, target_type, uuid4(), metadata)


def test_update_records_the_changed_field_names(admin):
    event = _record(admin, "update", {"fields": "opening_hours,phone"})

    assert event.action == AuditEvent.Action.UPDATE
    assert event.target_type == "store"
    assert event.metadata == {"fields": "opening_hours,phone"}


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"fields": ""},
        {"fields": "Phone"},
        {"fields": "phone, email"},
        {"fields": "phone,"},
        {"fields": "phone", "value": "+15145550110"},
        {"fields": ",".join(["opening_hours"] * 30)},
        {"fields": 3},
    ],
)
def test_update_refuses_anything_but_field_names(admin, metadata):
    with pytest.raises(ValidationError):
        _record(admin, "update", metadata)

    assert not AuditEvent.objects.exists()


def test_update_is_only_for_stores(admin):
    with pytest.raises(ValidationError):
        _record(admin, "update", {"fields": "phone"}, target_type="household")


def test_deactivate_records_reason_and_counts(admin):
    metadata = {
        "reason": "Closed for renovations",
        "listings_cancelled": 3,
        "reservations_cancelled": 5,
    }

    event = _record(admin, "deactivate", metadata)

    assert event.action == AuditEvent.Action.DEACTIVATE
    assert event.metadata == metadata


@pytest.mark.parametrize(
    "metadata",
    [
        {"reason": "Closed", "listings_cancelled": 0},
        {"reason": "", "listings_cancelled": 0, "reservations_cancelled": 0},
        {"reason": "x" * 501, "listings_cancelled": 0, "reservations_cancelled": 0},
        {
            "reason": "Owner SIN 123 456 789",
            "listings_cancelled": 0,
            "reservations_cancelled": 0,
        },
        {"reason": "Closed", "listings_cancelled": -1, "reservations_cancelled": 0},
        {"reason": "Closed", "listings_cancelled": "3", "reservations_cancelled": 0},
        {"reason": "Closed", "listings_cancelled": True, "reservations_cancelled": 0},
        {
            "reason": "Closed",
            "listings_cancelled": 0,
            "reservations_cancelled": 0,
            "extra": "x",
        },
    ],
)
def test_deactivate_refuses_invalid_metadata(admin, metadata):
    with pytest.raises(ValidationError):
        _record(admin, "deactivate", metadata)

    assert not AuditEvent.objects.exists()


def test_deactivate_is_only_for_stores(admin):
    metadata = {
        "reason": "Closed",
        "listings_cancelled": 0,
        "reservations_cancelled": 0,
    }
    with pytest.raises(ValidationError):
        _record(admin, "deactivate", metadata, target_type="household")


def test_store_reactivation_uses_the_store_reason_limit(admin):
    """No household rule is published here: stores have their own fixed limit."""
    event = _record(admin, "reactivate", {"reason": "x" * 500})

    assert event.metadata == {"reason": "x" * 500}


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"reason": ""},
        {"reason": "   "},
        {"reason": "x" * 501},
        {"reason": "Write to a@b.example"},
    ],
)
def test_store_reactivation_refuses_invalid_reasons(admin, metadata):
    with pytest.raises(ValidationError):
        _record(admin, "reactivate", metadata)
