# AI contribution: 50% or more AI-generated
# Code has been planned and written by AI, while I reviewed, edited, and tested the code
"""US-11 B.A.D.R. store seed tests."""

from io import StringIO

import pytest
from django.core.management import call_command
from modules.stores.models import Store


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
    assert store.phone
    assert store.email
    assert isinstance(store.opening_hours, dict)

    store.pickup_instructions = "Updated by an administrator."
    store.save(update_fields=["pickup_instructions"])
    call_command("seed_badr_store", stdout=output)

    assert Store.objects.count() == 1
    store.refresh_from_db()
    assert store.pickup_instructions == "Updated by an administrator."
