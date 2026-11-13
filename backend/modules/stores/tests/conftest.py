# AI contribution: 50% or more AI-generated
"""Shared admin and invitation-rule fixtures for partner decision workflows."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.rules.models import RuleSetVersion


@pytest.fixture
def admin():
    return UserFactory(role=User.Role.ADMIN)


@pytest.fixture
def invitation_rule(admin):
    return RuleSetVersion.objects.create(
        rule_type="invitations",
        version=1,
        values={"expires_after_days": 7},
        effective_from=timezone.now() - timedelta(days=1),
        created_by=admin,
    )
