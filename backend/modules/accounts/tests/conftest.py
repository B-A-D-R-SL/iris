# AI contribution: 50% or more AI-generated
"""US-04 fixtures exercise the real services with generated invitation data."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.utils import timezone

from modules.accounts import services
from modules.accounts.tests.factories import InvitationInputFactory, UserFactory
from modules.rules.models import RuleSetVersion


@pytest.fixture
def invitation_clock(monkeypatch):
    """Provide deterministic, aware time without waiting or changing production code."""
    clock = SimpleNamespace(now=datetime(2026, 11, 6, 15, tzinfo=UTC))
    monkeypatch.setattr(timezone, "now", lambda: clock.now)
    return clock


@pytest.fixture
def invitation_values():
    """Build recipient input without creating an account before acceptance."""
    return InvitationInputFactory()


@pytest.fixture
def invitation_model():
    """Resolve the model at test execution so absent #430 code does not stop collection."""
    return apps.get_model("accounts", "Invitation")


@pytest.fixture
def invitation_rule(db, invitation_clock):
    """Persist the required seven-day rule independently of seed/schema tests."""
    return RuleSetVersion.objects.create(
        rule_type="invitations",
        version=1,
        values={"expires_after_days": 7},
        effective_from=invitation_clock.now - timedelta(days=1),
        created_by=UserFactory(role="admin", password=None),
    )


@pytest.fixture
def issue_invitation(invitation_rule, invitation_model):
    """Create through the real public service and reload the persisted invitation."""

    def issue(**overrides):
        values = InvitationInputFactory(**overrides)
        token = services.create_invitation(**values)
        invitation = invitation_model.objects.get(
            token_hash=sha256(token.encode("utf-8")).hexdigest()
        )
        return token, invitation

    return issue
