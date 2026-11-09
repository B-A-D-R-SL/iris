# AI contribution: 50% or more AI-generated
"""US-04 creation, RuleSet lifetime, and token security acceptance tests."""

import base64
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from threading import Barrier

import pytest
from django.core.exceptions import ValidationError
from django.db import (
    DatabaseError,
    IntegrityError,
    close_old_connections,
    connection,
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


# rule: BR-INV-001
def test_new_rule_version_affects_new_invitations_only(
    invitation_rule, invitation_clock, issue_invitation
):
    """Persisted expiries do not move when a later lifetime version takes effect."""
    previous_token, previous = issue_invitation()
    invitation_rule.__class__.objects.create(
        rule_type="invitations",
        version=2,
        values={"expires_after_days": 2},
        effective_from=invitation_clock.now,
        created_by=invitation_rule.created_by,
    )

    current_token, current = issue_invitation()
    previous.refresh_from_db()

    assert previous.expires_at == invitation_clock.now + timedelta(days=7)
    assert current.expires_at == invitation_clock.now + timedelta(days=2)
    invitation_clock.now += timedelta(days=3)
    created = services.accept_invitation(previous_token, PASSWORD)
    assert created.email == previous.email
    with pytest.raises(ValidationError):
        services.accept_invitation(current_token, PASSWORD)


@pytest.mark.parametrize("role", User.Role.values)
def test_acceptance_creates_active_user_with_invited_identity_and_assignment(
    issue_invitation, invitation_clock, role
):
    """Every supported invitation role becomes the assigned role on a new account."""
    store = StoreFactory() if role.startswith("store_") else None
    token, invitation = issue_invitation(role=role, store=store)

    created = services.accept_invitation(token, PASSWORD)
    user = User.objects.get(email=invitation.email)
    invitation.refresh_from_db()

    assert created.pk == user.pk
    assert user.first_name == invitation.first_name
    assert user.last_name == invitation.last_name
    assert user.role == role
    assert user.store_id == (store.pk if store else None)
    assert user.is_active
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)
    assert invitation.accepted_at == invitation_clock.now
    assert User.objects.filter(email__iexact=invitation.email).count() == 1


def test_invitation_is_valid_immediately_before_expiration(
    issue_invitation, invitation_clock
):
    """The final instant before the saved expiry is still valid."""
    token, invitation = issue_invitation()
    invitation_clock.now = invitation.expires_at - timedelta(microseconds=1)

    created = services.accept_invitation(token, PASSWORD)

    assert created.email == invitation.email
    invitation.refresh_from_db()
    assert invitation.accepted_at == invitation_clock.now


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(microseconds=1)])
def test_expired_invitation_is_refused_without_consumption(
    issue_invitation, invitation_clock, offset
):
    """The saved expiry is exclusive, including its exact boundary."""
    token, invitation = issue_invitation()
    invitation_clock.now = invitation.expires_at + offset

    with pytest.raises(ValidationError):
        services.accept_invitation(token, PASSWORD)

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()


# rule: BR-INV-002
def test_used_invitation_cannot_change_the_created_account(issue_invitation):
    """Replaying a token cannot overwrite the password or account assignments."""
    token, invitation = issue_invitation()
    user = services.accept_invitation(token, PASSWORD)
    invitation.refresh_from_db()
    accepted_at = invitation.accepted_at
    before = User.objects.filter(pk=user.pk).values().get()

    with pytest.raises(ValidationError):
        services.accept_invitation(token, "replacement-password-429")

    assert User.objects.filter(pk=user.pk).values().get() == before
    invitation.refresh_from_db()
    assert invitation.accepted_at == accepted_at


@pytest.mark.parametrize(
    "kind", ["empty", "malformed", "unknown", "tampered", "non-string"]
)
def test_invalid_token_creates_no_user_and_leaves_valid_invitation_available(
    issue_invitation, kind
):
    """Neither an unrecognized link nor a changed token consumes another invitation."""
    token, invitation = issue_invitation()
    supplied = {
        "empty": "",
        "malformed": "not-a-token",
        "unknown": secrets.token_urlsafe(32),
        "tampered": ("A" if token[0] != "A" else "B") + token[1:],
        "non-string": None,
    }[kind]

    with pytest.raises(ValidationError):
        services.accept_invitation(supplied, PASSWORD)

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()


@pytest.mark.parametrize(
    "password", ["R7!aQ2xZ?", "password12345", "9274610385721", "", " " * 10]
)
def test_invalid_password_leaves_invitation_available_for_valid_retry(
    issue_invitation, password
):
    """Short, common and numeric-only passwords are refused without burning a link."""
    token, invitation = issue_invitation()

    with pytest.raises(ValidationError):
        services.accept_invitation(token, password)

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()
    created = services.accept_invitation(token, PASSWORD)
    assert created.check_password(PASSWORD)


def test_password_similarity_uses_the_invitation_recipient(issue_invitation):
    """Validation checks the prospective user's attributes before creating the account."""
    token, invitation = issue_invitation()

    with pytest.raises(ValidationError):
        services.accept_invitation(token, invitation.email)

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()


def test_valid_ten_character_password_is_accepted(issue_invitation, invitation_clock):
    """The configured minimum accepts a strong password at exactly ten characters."""
    token, invitation = issue_invitation()
    password = "R7!aQ2xZ?L"

    user = services.accept_invitation(token, password)

    assert user.check_password(password)
    invitation.refresh_from_db()
    assert invitation.accepted_at == invitation_clock.now


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


def test_failure_recording_acceptance_rolls_back_the_new_user(
    issue_invitation, invitation_model, monkeypatch
):
    """A database failure after user creation cannot leave a partially accepted link."""
    token, invitation = issue_invitation()

    def unavailable(*args, **kwargs):
        raise DatabaseError("acceptance write failed")

    monkeypatch.setattr(invitation_model, "save", unavailable)
    with pytest.raises(DatabaseError, match="acceptance write failed"):
        services.accept_invitation(token, PASSWORD)
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()


def test_unexpected_user_write_failure_is_not_reported_as_an_existing_email(
    issue_invitation, monkeypatch
):
    """Only recognized email constraints become the registered-email error."""
    token, invitation = issue_invitation()

    def unavailable(*args, **kwargs):
        raise IntegrityError("unexpected user write failure")

    monkeypatch.setattr(User.objects, "create_user", unavailable)
    with pytest.raises(IntegrityError, match="unexpected user write failure"):
        services.accept_invitation(token, PASSWORD)
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()


@pytest.mark.parametrize("is_active", [True, False])
# rule: BR-INV-003
def test_acceptance_refuses_an_email_registered_after_invitation_creation(
    issue_invitation, is_active
):
    """A later registered account, active or inactive, must never be overwritten."""
    token, invitation = issue_invitation()
    existing = UserFactory(email=invitation.email.upper(), is_active=is_active)
    before = User.objects.filter(pk=existing.pk).values().get()

    with pytest.raises(ValidationError):
        services.accept_invitation(token, PASSWORD)

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert User.objects.filter(pk=existing.pk).values().get() == before
    assert User.objects.filter(email__iexact=invitation.email).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_acceptance_creates_exactly_one_account(
    issue_invitation, invitation_clock
):
    """Competing requests cannot consume a token twice or overwrite the winner."""
    token, invitation = issue_invitation()
    barrier = Barrier(2)

    def accept(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            services.accept_invitation(token, f"invitation-429-password-{index}")
            return "accepted", index
        except ValidationError:
            return "refused", index
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(accept, range(2)))

    assert sorted(result for result, _ in outcomes) == ["accepted", "refused"]
    winner = next(index for result, index in outcomes if result == "accepted")
    user = User.objects.get(email=invitation.email)
    assert user.check_password(f"invitation-429-password-{winner}")
    assert User.objects.filter(email__iexact=invitation.email).count() == 1
    invitation.refresh_from_db()
    assert invitation.accepted_at == invitation_clock.now


@pytest.mark.django_db(transaction=True)
# rule: BR-INV-003
def test_competing_invitations_cannot_create_the_same_email_twice(issue_invitation):
    """Different token locks still rely on database email uniqueness at creation."""
    first_token, first = issue_invitation()
    second_token, second = issue_invitation(email=first.email)
    barrier = Barrier(2)

    def accept(token):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            services.accept_invitation(token, PASSWORD)
            return "accepted"
        except ValidationError as exc:
            return exc.code
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        outcomes = list(workers.map(accept, [first_token, second_token]))

    assert sorted(outcomes) == ["accepted", "email_already_registered"]
    assert User.objects.filter(email__iexact=first.email).count() == 1
    first.refresh_from_db()
    second.refresh_from_db()
    assert sum(link.accepted_at is not None for link in (first, second)) == 1
