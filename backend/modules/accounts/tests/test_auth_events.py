# AI contribution: 50% or more AI-generated
"""Completed browser and admin sessions log only the account UUID."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.signals import user_logged_out

from modules.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db
LOGIN = "/api/auth/browser/v1/auth/login"
SESSION = "/api/auth/browser/v1/auth/session"
PASSWORD = "test-auth-events-password"


def auth_events(caplog):
    return [record for record in caplog.records if record.name == "iris.auth"]


def test_browser_session_logs_each_completed_change_once(client, caplog):
    user = UserFactory(password=PASSWORD)
    with caplog.at_level("INFO", logger="iris.auth"):
        assert (
            client.post(
                LOGIN,
                {"email": user.email, "password": PASSWORD},
                content_type="application/json",
            ).status_code
            == 200
        )
        assert client.delete(SESSION).status_code == 401
    events = auth_events(caplog)
    assert [record.event for record in events] == ["sign_in_succeeded", "signed_out"]
    assert [record.user_id for record in events] == [user.pk, user.pk]
    assert user.email not in caplog.text
    assert PASSWORD not in caplog.text


def test_failed_login_does_not_log_success(client, caplog):
    user = UserFactory(password=PASSWORD)
    with caplog.at_level("INFO", logger="iris.auth"):
        assert (
            client.post(
                LOGIN,
                {"email": user.email, "password": "wrong"},
                content_type="application/json",
            ).status_code
            == 400
        )
    assert [record.event for record in auth_events(caplog)] == ["sign_in_failed"]


def test_admin_session_uses_the_same_events(client, caplog):
    user = UserFactory(password=PASSWORD, role="admin", is_staff=True)
    with caplog.at_level("INFO", logger="iris.auth"):
        assert (
            client.post(
                "/admin/login/", {"username": user.email, "password": PASSWORD}
            ).status_code
            == 302
        )
        assert client.post("/admin/logout/").status_code == 200
    events = auth_events(caplog)
    assert [record.event for record in events] == ["sign_in_succeeded", "signed_out"]
    assert [record.user_id for record in events] == [user.pk, user.pk]


@pytest.mark.parametrize("user", [None, AnonymousUser()])
def test_anonymous_logout_has_no_account_event(user, caplog):
    with caplog.at_level("INFO", logger="iris.auth"):
        user_logged_out.send(sender=type(user), request=None, user=user)
    assert auth_events(caplog) == []
