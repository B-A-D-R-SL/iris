# AI contribution: 50% or more AI-generated
"""US-03 / T-01.03.1: observable reset link and account-enumeration contracts."""

from datetime import datetime, timedelta
from urllib.parse import urlsplit

import pytest
from allauth.account.forms import default_token_generator
from allauth.account.utils import user_pk_to_url_str
from django.contrib.auth.hashers import identify_hasher

from adapters.mailer.fake import get_fake_mailer
from modules.accounts.tests.factories import UserFactory
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email

pytestmark = pytest.mark.django_db
REQUEST = "/api/auth/browser/v1/auth/password/request"
RESET = "/api/auth/browser/v1/auth/password/reset"
PASSWORD = "new-synthetic-password-427!"


def key_for(user):
    return f"{user_pk_to_url_str(user)}-{default_token_generator.make_token(user)}"


def post_reset(client, key, password=PASSWORD):
    return client.post(
        RESET, {"key": key, "password": password}, content_type="application/json"
    )


def test_requested_link_uses_trusted_origin_and_queued_saved_language(
    client, queued_reset, django_capture_on_commit_callbacks, settings
):
    # rule: BR-NOTIF-002 / BR-NOTIF-003: after commit, saved language, trusted URL.
    user = UserFactory(preferred_language="en")
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            REQUEST, {"email": user.email.upper()}, content_type="application/json"
        )
        assert response.status_code == 200
        assert queued_reset == []
    [job] = queued_reset
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.language == "en" and log.user_id == user.pk
    url = job["context"]["reset_url"]
    assert url.startswith(settings.PUBLIC_APP_ORIGIN + "/reset-password/")
    assert log.status == "pending" and get_fake_mailer().sent == []
    send_email(None, **job)
    [message] = get_fake_mailer().sent
    assert url in message["text"]
    key = urlsplit(url).path.removeprefix("/reset-password/")
    assert post_reset(client, key).status_code == 401
    user.refresh_from_db()
    assert user.check_password(PASSWORD)
    assert identify_hasher(user.password).algorithm == "argon2"
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize("active", [True, False])
def test_request_response_does_not_disclose_existing_or_inactive_email(
    client, queued_reset, django_capture_on_commit_callbacks, active
):
    user = UserFactory(is_active=active)
    with django_capture_on_commit_callbacks(execute=True):
        known = client.post(
            REQUEST, {"email": user.email}, content_type="application/json"
        )
        unknown = client.post(
            REQUEST,
            {"email": "unknown-reset@example.test"},
            content_type="application/json",
        )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"status": 200}
    assert len(queued_reset) == (1 if active else 0)


@pytest.mark.parametrize("age,expected", [(3599, 401), (3600, 401), (3601, 400)])
def test_reset_link_is_valid_for_sixty_minutes(client, monkeypatch, age, expected):
    user = UserFactory()
    # Django's token generator deliberately uses naive UTC internally.
    issued = datetime(2026, 11, 25, 12)  # noqa: DTZ001
    monkeypatch.setattr(default_token_generator, "_now", lambda: issued)
    key = key_for(user)
    monkeypatch.setattr(
        default_token_generator, "_now", lambda: issued + timedelta(seconds=age)
    )
    response = post_reset(client, key)
    assert response.status_code == expected
    user.refresh_from_db()
    assert user.check_password(PASSWORD) is (expected == 401)


@pytest.mark.parametrize("same_password", [False, True])
def test_reset_link_is_single_use_even_when_password_is_unchanged(
    client, same_password
):
    user = UserFactory(
        password=PASSWORD if same_password else "old-synthetic-password-427"
    )
    key = key_for(user)
    assert post_reset(client, key).status_code == 401
    assert post_reset(client, key, "another-synthetic-password-752").status_code == 400
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_inactive_account_cannot_use_a_previously_issued_link(client):
    user = UserFactory()
    key = key_for(user)
    user.is_active = False
    user.save(update_fields=["is_active"])
    original = user.password
    assert post_reset(client, key).status_code == 400
    user.refresh_from_db()
    assert user.password == original


def test_inactive_account_key_lookup_does_not_expose_its_profile(client):
    user = UserFactory()
    key = key_for(user)
    user.is_active = False
    user.save(update_fields=["is_active"])
    response = client.get(RESET, HTTP_X_PASSWORD_RESET_KEY=key)
    assert response.status_code == 400
    assert "data" not in response.json()
    assert user.email not in response.content.decode()


@pytest.mark.parametrize(
    "password", [{"nested": "synthetic-password-427"}, ["synthetic-password-427"]]
)
def test_non_string_password_is_rejected_without_consuming_link(client, password):
    user = UserFactory()
    key = key_for(user)
    original = user.password
    assert post_reset(client, key, password).status_code == 400
    user.refresh_from_db()
    assert user.password == original
    assert post_reset(client, key).status_code == 401
