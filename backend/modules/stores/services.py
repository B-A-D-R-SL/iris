# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Validated write operations for the stores module."""

from django.db import transaction

from modules.stores.models import Store


@transaction.atomic
def save_store(store: Store) -> Store:
    """Validate and persist a Store submitted through Django admin."""
    store.full_clean()
    store.save()
    return store
