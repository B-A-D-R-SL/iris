# AI contribution: 50% or more AI-generated
"""US-33 fixtures: saved test records, with account assignments ONLY in tests."""

from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from django.utils import timezone, translation

from modules.categories.models import Category
from modules.categories.tests.factories import CategoryFactory
from modules.listings.domain.posting import ListingInput
from modules.listings.tests.factories import create_staff_user
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish
from modules.stores.models import Store
from modules.stores.tests.factories import StoreFactory

NOW = datetime(2026, 10, 27, 18, tzinfo=UTC)


@pytest.fixture
def posting_case(db: Any, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    store = cast(Store, StoreFactory())
    category = cast(Category, CategoryFactory())
    user: Any = create_staff_user()
    # Default auth.User has no US-01 fields. These assignments are deliberately
    # transient: force_authenticate uses this instance, real sessions don't.
    monkeypatch.setattr(user, "role", "store_staff", raising=False)
    monkeypatch.setattr(user, "store_id", store.pk, raising=False)
    for rule_type in ("listing_posting", "listing_safety"):
        publish(
            rule_type,
            deepcopy(DEFAULT_RULE_VALUES[rule_type]),
            user,
            effective_from=NOW - timedelta(days=1),
        )
    data = ListingInput(
        category=category.pk,
        title="Surplus bread",
        quantity=5,
        pickup_start=NOW + timedelta(hours=1),
        pickup_end=NOW + timedelta(hours=3),
        best_before=timezone.localdate(NOW),
        safe_and_allowed=True,
    )
    with translation.override("en"):
        yield SimpleNamespace(
            user=user, store=store, category=category, data=data, now=NOW
        )
