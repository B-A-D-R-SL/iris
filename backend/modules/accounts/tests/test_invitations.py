# AI contribution: 50% or more AI-generated
"""US-04 creation, RuleSet lifetime, and token security acceptance tests."""

import secrets
from datetime import timedelta
from hashlib import sha256

import pytest
from django.db import (
    IntegrityError,
    transaction,
)

from modules.accounts.models import User

pytestmark = pytest.mark.django_db
PASSWORD = "test-invitation-429"


@pytest.mark.parametrize("role", [User.Role.STORE_STAFF, User.Role.STORE_MANAGER])
def test_database_rejects_a_store_invitation_without_a_store(
    invitation_model, invitation_values, invitation_clock, role
):
    """The required store is a database rule even when full_clean is bypassed."""
    with pytest.raises(IntegrityError), transaction.atomic():
        invitation_model.objects.create(
            **{**invitation_values, "role": role},
            token_hash=sha256(secrets.token_bytes(32)).hexdigest(),
            expires_at=invitation_clock.now + timedelta(days=7),
        )
    assert invitation_model.objects.count() == 0
