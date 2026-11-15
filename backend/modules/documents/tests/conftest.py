# AI contribution: 50% or more AI-generated
"""Shared fixtures for documents tests: the notice_upload rule and staff users."""

from collections.abc import Callable
from copy import deepcopy
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.rules.domain.schemas import DEFAULT_RULE_VALUES
from modules.rules.services import publish


@pytest.fixture
def publish_notice_rule(db: Any) -> Callable[..., None]:
    """Publish a notice_upload version: the defaults, with any value changed."""
    publisher: Any = UserFactory(role="admin")
    published = 0

    def _publish(**changes: Any) -> None:
        nonlocal published
        published += 1
        values = deepcopy(DEFAULT_RULE_VALUES["notice_upload"]) | changes
        # Each later call takes effect after the previous one.
        effective = timezone.now() - timedelta(days=1) + timedelta(minutes=published)
        publish("notice_upload", values, publisher, effective_from=effective)

    return _publish


@pytest.fixture
def notice_rule(publish_notice_rule: Callable[..., None]) -> None:
    publish_notice_rule()


@pytest.fixture
def worker(db: Any) -> Any:
    return UserFactory(role="intake_worker")
