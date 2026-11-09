# AI contribution: 50% or more AI-generated
"""US-04 creation, RuleSet lifetime, and token security acceptance tests."""

import base64
import secrets
from datetime import timedelta
from hashlib import sha256

import pytest
from django.core.exceptions import ValidationError
from django.db import (
    IntegrityError,
    transaction,
)
from django.utils import timezone

from modules.accounts import services
from modules.accounts.models import User
from modules.accounts.tests.factories import UserFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db
PASSWORD = "test-invitation-429"


def test_creation_saves_recipient_assignment_and_only_token_hash(
    issue_invitation, invitation_clock, invitation_values
):
    """An invitation carries its recipient and seven-day expiry without creating a user."""
    store = StoreFactory()
    inviter = UserFactory(role=User.Role.ADMIN)
    token, invitation = issue_invitation(
        **{
            **invitation_values,
            "email": invitation_values["email"].upper(),
            "role": User.Role.STORE_MANAGER,
            "store": store,
            "invited_by": inviter,
        }
    )

    assert invitation.email == invitation_values["email"].lower()
    assert invitation.first_name == invitation_values["first_name"]
    assert invitation.last_name == invitation_values["last_name"]
    assert invitation.role == User.Role.STORE_MANAGER
    assert invitation.store_id == store.pk
    assert invitation.invited_by_id == inviter.pk
    assert invitation.accepted_at is None
    assert timezone.is_aware(invitation.expires_at)
    assert invitation.expires_at == invitation_clock.now + timedelta(days=7)
    assert invitation.token_hash == sha256(token.encode("utf-8")).hexdigest()
    assert (
        token
        not in invitation.__class__.objects.values().get(pk=invitation.pk).values()
    )
    assert not User.objects.filter(email__iexact=invitation.email).exists()


def test_tokens_encode_32_random_bytes_and_are_distinct(issue_invitation):
    """URL-safe links encode the required bytes rather than a fixed 32-character token."""
    first_token, first = issue_invitation()
    second_token, second = issue_invitation()

    for token in (first_token, second_token):
        assert len(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))) == 32
    assert first_token != second_token
    assert first.token_hash != second.token_hash


@pytest.mark.parametrize("role", [User.Role.STORE_STAFF, User.Role.STORE_MANAGER])
def test_store_role_invitation_requires_store(
    invitation_rule, invitation_model, invitation_values, role
):
    """A store role cannot be issued without its required store assignment."""
    with pytest.raises(ValidationError):
        services.create_invitation(**{**invitation_values, "role": role})

    assert invitation_model.objects.count() == 0
    assert not User.objects.filter(email=invitation_values["email"]).exists()


def test_creation_refuses_unknown_role(
    invitation_rule, invitation_model, invitation_values
):
    """Invalid role input cannot produce an invitation with undefined privileges."""
    with pytest.raises(ValidationError):
        services.create_invitation(**{**invitation_values, "role": "unsupported"})

    assert invitation_model.objects.count() == 0


@pytest.mark.parametrize("is_active", [True, False])
def test_creation_refuses_registered_email_regardless_of_case_or_activity(
    invitation_rule, invitation_model, invitation_values, is_active
):
    """Invitations are restricted to new accounts, including when an old account is inactive."""
    existing = UserFactory(email=invitation_values["email"], is_active=is_active)
    before = User.objects.filter(pk=existing.pk).values().get()

    with pytest.raises(ValidationError):
        services.create_invitation(
            **{**invitation_values, "email": existing.email.upper()}
        )

    assert User.objects.filter(pk=existing.pk).values().get() == before
    assert invitation_model.objects.count() == 0


def test_creation_requires_active_lifetime_rule(
    invitation_clock, invitation_model, invitation_values
):
    """A missing RuleSet cannot silently use a hardcoded lifetime or partially save data."""
    with pytest.raises(ValidationError):
        services.create_invitation(**invitation_values)

    assert invitation_model.objects.count() == 0
    assert not User.objects.exists()


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"expires_after_days": 0},
        {"expires_after_days": False},
        {"expires_after_days": "7"},
        {"expires_after_days": 10**12},
    ],
)
def test_corrupt_lifetime_configuration_refuses_creation_without_partial_writes(
    invitation_rule, invitation_model, invitation_clock, invitation_values, values
):
    """Even a directly inserted invalid rule cannot produce an unsafe expiry."""
    invitation_rule.__class__.objects.create(
        rule_type="invitations",
        version=2,
        values=values,
        effective_from=invitation_clock.now,
        created_by=invitation_rule.created_by,
    )
    with pytest.raises(ValidationError) as caught:
        services.create_invitation(**invitation_values)
    assert caught.value.code == "invitation_unavailable"
    assert invitation_model.objects.count() == 0


def test_token_hash_uniqueness_is_enforced_in_the_database(
    issue_invitation, invitation_model, invitation_values
):
    """Direct writes cannot introduce two invitations with the same token hash."""
    _, invitation = issue_invitation()
    with pytest.raises(IntegrityError), transaction.atomic():
        invitation_model.objects.create(
            **invitation_values,
            token_hash=invitation.token_hash,
            expires_at=invitation.expires_at,
        )
    assert invitation_model.objects.count() == 1


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
