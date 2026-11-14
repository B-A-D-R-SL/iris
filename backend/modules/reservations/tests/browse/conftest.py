# AI contribution: 50% or more AI-generated
"""Fixtures for the GET /api/listings/ tests in this folder (US-36)."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from modules.accounts.tests.factories import UserFactory
from modules.reservations.tests.browse.helpers import NOW, _household


@pytest.fixture(autouse=True)
def frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every request in these tests happens at NOW."""
    monkeypatch.setattr(timezone, "now", lambda: NOW)


@pytest.fixture
def client() -> APIClient:
    """An API client that asks for English messages."""
    return APIClient(HTTP_ACCEPT_LANGUAGE="en")


@pytest.fixture
def approved(client: APIClient) -> APIClient:
    """A client signed in, through a real session, as an approved household."""
    user = UserFactory(role="beneficiary")
    _household(user)
    client.force_login(user)
    return client
