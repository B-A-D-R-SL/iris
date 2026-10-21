# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Validated write operations for the stores module."""

from django.db import transaction

from modules.stores.models import Store

BADR_STORE_DEFAULTS = {
    "name": "B.A.D.R.",
    "street_number": "0000",
    "street_name": "rue Exemple",
    "city": "Montreal",
    "postal_code": "H0H 0H0",
    "phone": "514-555-0100",
    "email": "badr-store@example.test",
    "opening_hours": {},
    "is_active": True,
}


@transaction.atomic
def save_store(store: Store) -> Store:
    """Validate and persist a Store submitted through Django admin."""
    store.full_clean()
    store.save()
    return store


@transaction.atomic
def ensure_badr_store() -> tuple[Store, bool]:
    """Create the placeholder B.A.D.R. store once without changing later edits."""
    return Store.objects.get_or_create(is_badr=True, defaults=BADR_STORE_DEFAULTS)
