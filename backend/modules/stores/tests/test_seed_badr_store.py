# AI contribution: 50% or more AI-generated
# Code has been planned and written by AI, while I reviewed, edited, and tested the code
"""US-11 B.A.D.R. store seed tests."""

from io import StringIO
from typing import cast

import pytest
from django.core.management import call_command
from django.forms.models import model_to_dict

from modules.stores.models import Store
from modules.stores.tests.factories import StoreFactory


@pytest.mark.django_db
def test_seed_creates_one_active_badr_store_and_is_idempotent() -> None:
    """A second seed keeps the first store and any later admin edits."""
    output = StringIO()
    call_command("seed_badr_store", stdout=output)

    store = Store.objects.get(is_badr=True)
    assert Store.objects.count() == 1
    assert store.name == "B.A.D.R."
    assert store.is_active is True
    assert store.street_number == "0000"
    assert store.street_name == "rue Exemple"
    assert store.city == "Montreal"
    assert store.postal_code == "H0H 0H0"
    assert store.phone == "514-555-0100"
    assert store.email == "badr-store@example.test"
    assert store.opening_hours == {}
    assert store.unit is None
    assert store.pickup_instructions is None

    original_id = store.pk
    store.name = "B.A.D.R. Montréal"
    store.is_active = False
    store.pickup_instructions = "Updated by an administrator."
    store.save(update_fields=["name", "is_active", "pickup_instructions"])
    call_command("seed_badr_store", stdout=output)

    assert Store.objects.count() == 1
    store.refresh_from_db()
    assert store.pk == original_id
    assert store.name == "B.A.D.R. Montréal"
    assert store.is_active is False
    assert store.pickup_instructions == "Updated by an administrator."
    assert "Already exists" in output.getvalue()


@pytest.mark.django_db
def test_seed_leaves_partner_store_unchanged() -> None:
    """Seeding B.A.D.R. must neither reuse nor modify an ordinary partner."""
    partner = cast(Store, StoreFactory())
    original_fields = model_to_dict(partner)

    call_command("seed_badr_store", stdout=StringIO())

    partner.refresh_from_db()
    assert Store.objects.count() == 2
    assert partner.is_badr is False
    assert model_to_dict(partner) == original_fields
    assert Store.objects.get(is_badr=True).pk != partner.pk
