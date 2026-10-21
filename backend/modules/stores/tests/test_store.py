# AI contribution: 50% or more AI-generated
# Code has been planned and written by AI, while I reviewed, edited, and tested the code

"""US-11 store persistence and data-integrity tests."""

import uuid
from typing import cast

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from modules.stores.models import Store
from modules.stores.tests.factories import StoreFactory


@pytest.fixture
def store_fields() -> dict[str, object]:
    """Provide generated store details that are safe for an isolated test database."""
    return {
        "name": "Example Partner",
        "street_number": "100",
        "street_name": "Example Street",
        "unit": "2",
        "city": "Montréal",
        "postal_code": "H2X 1Y4",
        "phone": "514-555-0100",
        "email": "partner@example.test",
        "opening_hours": {"mon": [["09:00", "17:00"]], "sun": []},
        "pickup_instructions": "Use the side door.",
    }


@pytest.mark.django_db
def test_store_persists_every_us11_field(store_fields: dict[str, object]) -> None:
    """Keep the full store profile available to future accounts and listings."""
    store = Store.objects.create(**store_fields, is_badr=True, is_active=False)
    saved = Store.objects.get(pk=store.pk)

    assert isinstance(saved.pk, uuid.UUID)
    for field, expected in store_fields.items():
        assert getattr(saved, field) == expected
    assert saved.is_badr is True
    assert saved.is_active is False
    assert saved.created_at is not None
    assert saved.updated_at is not None


@pytest.mark.django_db
def test_store_defaults_and_optional_address_fields(
    store_fields: dict[str, object],
) -> None:
    """An ordinary partner remains active without an apartment or pickup note."""
    store_fields.pop("unit")
    store_fields.pop("pickup_instructions")
    store = Store.objects.create(**store_fields)
    store.refresh_from_db()

    assert store.unit is None
    assert store.pickup_instructions is None
    assert store.is_badr is False
    assert store.is_active is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [("name", ""), ("email", "not-an-email"), ("postal_code", "invalid")],
)
def test_store_rejects_invalid_required_details(
    store_fields: dict[str, object], field: str, value: str
) -> None:
    """Catch blank or malformed details before an administrator saves them."""
    store_fields[field] = value
    store = Store(**store_fields)

    with pytest.raises(ValidationError) as error:
        store.full_clean()

    assert field in error.value.message_dict


@pytest.mark.django_db
def test_database_allows_only_one_badr_store(store_fields: dict[str, object]) -> None:
    """Protect the single B.A.D.R. identity even outside Django form validation."""
    Store.objects.create(**store_fields, is_badr=True)
    second_fields = {**store_fields, "name": "Another B.A.D.R. row"}

    with pytest.raises(IntegrityError), transaction.atomic():
        Store.objects.create(**second_fields, is_badr=True)

    assert Store.objects.filter(is_badr=True).count() == 1


@pytest.mark.django_db
def test_factory_creates_multiple_partners_with_case_insensitive_email() -> None:
    """Partner stores remain repeatable while PostgreSQL compares email without case."""
    first = cast(Store, StoreFactory(email="Partner@Example.test"))
    second = cast(Store, StoreFactory())

    assert first.pk != second.pk
    assert Store.objects.filter(is_badr=False).count() == 2
    assert Store.objects.get(email="partner@example.test") == first
