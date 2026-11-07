# AI contribution: 50% or more AI-generated
"""US-04 public API, role and PostgreSQL integration contracts."""

from typing import Any

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from modules.accounts.models import User
from modules.accounts.tests.factories import InvitationInputFactory, UserFactory
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db
URL = "/api/invitations/accept/"
LOGIN = "/api/auth/browser/v1/auth/login"
PASSWORD = "invitation-test-password-429"
CALLER_ROLES = (None, *User.Role.values)


def post(client: APIClient, token: Any, password: Any = PASSWORD, **extra: Any) -> Any:
    """Send the token and password without trusting any extra identity fields."""
    return client.post(
        URL,
        {"token": token, "password": password, **extra},
        format="json",
        HTTP_ACCEPT_LANGUAGE="en",
    )


def assert_error(response: Any, code: str) -> dict[str, Any]:
    """Check the shared error envelope before inspecting persisted state."""
    assert response.status_code == 400
    body = response.json()
    assert set(body) == {"code", "message", "fields"}
    assert body["code"] == code
    assert isinstance(body["message"], str) and body["message"].strip()
    assert isinstance(body["fields"], dict)
    return body


@pytest.mark.parametrize("caller_role", CALLER_ROLES)
def test_valid_token_is_allowed_for_anonymous_and_every_role(
    issue_invitation: Any, caller_role: str | None
) -> None:
    """The saved invitation controls the new account, independently of its caller."""
    invited_store: Any = StoreFactory()
    token, invitation = issue_invitation(
        role=User.Role.STORE_MANAGER, store=invited_store
    )
    client = APIClient()
    caller: Any = None
    if caller_role:
        store = StoreFactory() if caller_role.startswith("store_") else None
        caller = UserFactory(role=caller_role, store=store)
        client.force_authenticate(caller)
    before = list(User.objects.filter(pk=caller.pk).values()) if caller else []

    response = post(client, token)

    assert response.status_code == 200
    recipient = User.objects.get(email=invitation.email)
    assert recipient.role == User.Role.STORE_MANAGER
    assert recipient.store_id == invited_store.pk
    assert recipient.is_active and recipient.check_password(PASSWORD)
    if caller:
        assert list(User.objects.filter(pk=caller.pk).values()) == before
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize("caller_role", CALLER_ROLES)
def test_invalid_token_is_refused_for_anonymous_and_every_role(
    issue_invitation: Any, caller_role: str | None
) -> None:
    """An existing session or privileged role cannot replace a valid token."""
    token, invitation = issue_invitation()
    client = APIClient()
    if caller_role:
        store = StoreFactory() if caller_role.startswith("store_") else None
        client.force_authenticate(UserFactory(role=caller_role, store=store))
    before = list(User.objects.order_by("pk").values())
    invalid = token[:-1] + ("A" if token[-1] != "A" else "B")

    assert_error(post(client, invalid), "invitation_invalid")

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert list(User.objects.order_by("pk").values()) == before


def test_acceptance_then_sign_in_uses_the_new_account_and_database(
    issue_invitation: Any,
) -> None:
    """Exercise invitation service, HTTP acceptance, stored password and US-01 sign-in."""
    token, invitation = issue_invitation()
    client = APIClient(enforce_csrf_checks=True)

    response = post(client, token)

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert token not in response.content.decode()
    assert PASSWORD not in response.content.decode()
    invitation.refresh_from_db()
    recipient = User.objects.get(email=invitation.email)
    assert invitation.accepted_at is not None
    assert recipient.first_name == invitation.first_name
    assert recipient.last_name == invitation.last_name
    assert recipient.role == invitation.role and recipient.store_id is None
    assert recipient.is_active and recipient.check_password(PASSWORD)
    assert recipient.password != PASSWORD

    signed_in = APIClient()
    login = signed_in.post(
        LOGIN, {"email": recipient.email, "password": PASSWORD}, format="json"
    )
    assert login.status_code == 200
    me = signed_in.get("/api/me/")
    assert me.status_code == 200
    assert me.json() == {
        "id": str(recipient.pk),
        "name": recipient.get_full_name(),
        "role": invitation.role,
        "store": None,
        "language": "fr",
    }


def test_expired_link_is_refused_without_creating_a_user(
    issue_invitation: Any, invitation_clock: Any
) -> None:
    """The exact saved expiry is already outside the acceptance window."""
    token, invitation = issue_invitation()
    invitation_clock.now = invitation.expires_at
    before = list(User.objects.order_by("pk").values())

    assert_error(post(APIClient(), token), "invitation_expired")

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert list(User.objects.order_by("pk").values()) == before


def test_used_link_is_refused_without_rewriting_the_created_account(
    issue_invitation: Any,
) -> None:
    """Replaying the same link cannot change the accepted account's password."""
    token, invitation = issue_invitation()
    client = APIClient()
    assert post(client, token).status_code == 200
    invitation.refresh_from_db()
    accepted_at = invitation.accepted_at
    before = list(User.objects.order_by("pk").values())

    assert_error(post(client, token, "different-valid-password-429"), "invitation_used")

    invitation.refresh_from_db()
    assert invitation.accepted_at == accepted_at
    assert list(User.objects.order_by("pk").values()) == before


@pytest.mark.parametrize("field", ["token", "password"])
def test_required_fields_are_refused_without_consuming_the_invitation(
    issue_invitation: Any, field: str
) -> None:
    """Missing request fields leave the invitation available for a corrected request."""
    token, invitation = issue_invitation()
    values = {"token": token, "password": PASSWORD}
    del values[field]
    before = list(User.objects.order_by("pk").values())

    response = APIClient().post(URL, values, format="json", HTTP_ACCEPT_LANGUAGE="en")

    body = assert_error(response, "validation_error")
    assert field in body["fields"]
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert list(User.objects.order_by("pk").values()) == before


@pytest.mark.parametrize(("field", "value"), [("token", None), ("password", None)])
def test_null_fields_are_refused_without_account_writes(
    issue_invitation: Any, field: str, value: Any
) -> None:
    """Null values are input errors rather than unexpected server failures."""
    token, invitation = issue_invitation()
    values = {"token": token, "password": PASSWORD, field: value}
    before = list(User.objects.order_by("pk").values())

    response = APIClient().post(URL, values, format="json", HTTP_ACCEPT_LANGUAGE="en")

    assert field in assert_error(response, "validation_error")["fields"]
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert list(User.objects.order_by("pk").values()) == before


def test_password_validation_failure_does_not_consume_the_invitation(
    issue_invitation: Any,
) -> None:
    """A rejected password can be corrected using the original unused token."""
    token, invitation = issue_invitation()
    before = list(User.objects.order_by("pk").values())

    body = assert_error(post(APIClient(), token, "short"), "validation_error")

    assert "password" in body["fields"]
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert list(User.objects.order_by("pk").values()) == before
    assert post(APIClient(), token).status_code == 200


@pytest.mark.parametrize("field", ["role", "store", "email"])
def test_request_cannot_override_invitation_identity_or_privileges(
    issue_invitation: Any, field: str
) -> None:
    """The endpoint refuses client-selected recipient identity and role/store values."""
    token, invitation = issue_invitation()
    other_store: Any = StoreFactory()
    other_recipient: Any = InvitationInputFactory()
    value = {
        "role": User.Role.ADMIN,
        "store": str(other_store.pk),
        "email": other_recipient["email"],
    }[field]
    before = list(User.objects.order_by("pk").values())

    assert_error(post(APIClient(), token, **{field: value}), "validation_error")

    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert list(User.objects.order_by("pk").values()) == before


@pytest.mark.parametrize("is_active", [True, False])
def test_existing_email_is_refused_even_when_registered_after_invitation(
    issue_invitation: Any, is_active: bool
) -> None:
    """Neither an active nor an inactive existing account may be overwritten."""
    token, invitation = issue_invitation()
    existing: Any = UserFactory(
        email=invitation.email.upper(), role=User.Role.ADMIN, is_active=is_active
    )
    before = list(User.objects.order_by("pk").values())

    assert_error(post(APIClient(), token), "email_already_registered")

    invitation.refresh_from_db()
    existing.refresh_from_db()
    assert invitation.accepted_at is None
    assert existing.is_active == is_active
    assert list(User.objects.order_by("pk").values()) == before


def test_authenticated_session_requires_csrf_before_acceptance(
    issue_invitation: Any,
) -> None:
    """A public endpoint still protects an existing cookie-authenticated session."""
    token, invitation = issue_invitation()
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(UserFactory(role=User.Role.ADMIN))
    before = list(User.objects.order_by("pk").values())

    response = post(client, token)

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert list(User.objects.order_by("pk").values()) == before


def test_acceptance_with_csrf_preserves_the_existing_browser_session(
    issue_invitation: Any,
) -> None:
    """Accept a new recipient without silently switching the signed-in caller."""
    token, invitation = issue_invitation()
    caller: Any = UserFactory(role=User.Role.ADMIN)
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(caller)
    csrf_token = "c" * 32
    client.cookies[settings.CSRF_COOKIE_NAME] = csrf_token
    before = User.objects.filter(pk=caller.pk).values().get()

    response = client.post(
        URL,
        {"token": token, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert client.session["_auth_user_id"] == str(caller.pk)
    assert User.objects.filter(pk=caller.pk).values().get() == before
    assert User.objects.get(email=invitation.email).check_password(PASSWORD)


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_acceptance_only_allows_post(method: str) -> None:
    """Other HTTP methods cannot consume invitations or mutate accounts."""
    before = list(User.objects.order_by("pk").values())

    response = getattr(APIClient(), method)(URL)

    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
    assert list(User.objects.order_by("pk").values()) == before


def test_expired_link_errors_follow_the_requested_language(
    issue_invitation: Any, invitation_clock: Any
) -> None:
    """Both languages keep the same machine-readable failure without consuming a token."""
    token, invitation = issue_invitation()
    invitation_clock.now = invitation.expires_at
    messages = []
    for language in ("fr", "en"):
        response = APIClient().post(
            URL,
            {"token": token, "password": PASSWORD},
            format="json",
            HTTP_ACCEPT_LANGUAGE=language,
        )
        messages.append(assert_error(response, "invitation_expired")["message"])

    assert messages[0] != messages[1]
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
