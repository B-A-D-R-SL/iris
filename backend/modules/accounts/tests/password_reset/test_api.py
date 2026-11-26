# AI contribution: 50% or more AI-generated
"""US-03 / T-01.03.1: access, validation and failure paths in allauth's API."""

import json
import logging

import pytest
from django.test import Client

from modules.accounts.queries import STORE_ROLES
from modules.accounts.roles import UserRole
from modules.accounts.tests.factories import UserFactory
from modules.notifications.models import EmailLog
from modules.notifications.tasks import send_email
from modules.stores.tests.factories import StoreFactory

from .test_flow import PASSWORD, REQUEST, RESET, key_for, post_reset

pytestmark = pytest.mark.django_db
SESSION = "/api/auth/browser/v1/auth/session"
UNKNOWN_EMAIL = "unknown-recovery@example.test"


@pytest.fixture(params=[None, *UserRole.values], ids=["anonymous", *UserRole.values])
def caller(client, request):
    role = request.param
    if role is None:
        return None
    store = StoreFactory() if role in STORE_ROLES else None
    user = UserFactory(role=role, store=store)
    client.force_login(user)
    return user


def request_reset(client, email, **headers):
    return client.post(
        REQUEST, {"email": email}, content_type="application/json", **headers
    )


def test_each_role_can_request_a_reset_without_disclosing_account_existence(
    client, caller, queued_reset, django_capture_on_commit_callbacks
):
    target = caller if caller is not None else UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        known = request_reset(client, target.email)
        unknown = request_reset(client, UNKNOWN_EMAIL)

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"status": 200}
    [job] = queued_reset
    log = EmailLog.objects.get(pk=job["email_log_id"])
    assert log.template_key == "password_reset"
    assert log.user_id == target.pk


def test_each_role_is_refused_a_reset_request_with_an_invalid_address(client, caller):
    response = request_reset(client, "not-an-address")

    assert response.status_code == 400
    assert any(error.get("param") == "email" for error in response.json()["errors"])
    assert not EmailLog.objects.filter(template_key="password_reset").exists()


# BR-NOTIF-003: a valid request host cannot change the origin of a reset link.
def test_reset_link_uses_the_configured_origin_even_on_another_allowed_host(
    client, settings, queued_reset, django_capture_on_commit_callbacks
):
    alternate_host = "alternate-iris.example.test"
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, alternate_host]
    user = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        response = request_reset(client, user.email, HTTP_HOST=alternate_host)

    assert response.status_code == 200
    [job] = queued_reset
    assert job["context"]["reset_url"].startswith(
        settings.PUBLIC_APP_ORIGIN + "/reset-password/"
    )


def test_each_role_can_validate_a_reset_key_without_changing_the_account(
    client, caller
):
    target = UserFactory()
    original_hash = target.password

    allowed = client.get(RESET, HTTP_X_PASSWORD_RESET_KEY=key_for(target))
    refused = client.get(RESET, HTTP_X_PASSWORD_RESET_KEY="invalid-key")

    assert allowed.status_code == 200
    assert allowed.json()["data"]["user"]["id"] == str(target.pk)
    assert refused.status_code == 400
    assert "data" not in refused.json()
    target.refresh_from_db()
    assert target.password == original_hash


def test_each_role_can_reset_the_key_holders_password_without_switching_sessions(
    client, caller
):
    target = UserFactory()
    caller_hash = caller.password if caller is not None else None

    response = post_reset(client, key_for(target))

    target.refresh_from_db()
    assert target.check_password(PASSWORD)
    profile = client.get("/api/me/")
    if caller is None:
        assert response.status_code == profile.status_code == 401
    else:
        assert response.status_code == profile.status_code == 200
        assert profile.json()["id"] == str(caller.pk)
        caller.refresh_from_db()
        assert caller.password == caller_hash


def test_each_role_cannot_change_any_password_without_a_valid_key(client, caller):
    target = UserFactory()
    original_hash = target.password
    caller_hash = caller.password if caller is not None else None

    response = post_reset(client, "invalid-key")

    assert response.status_code == 400
    assert "data" not in response.json()
    target.refresh_from_db()
    assert target.password == original_hash
    if caller is not None:
        caller.refresh_from_db()
        assert caller.password == caller_hash


def test_reset_request_requires_browser_csrf(
    settings, queued_reset, django_capture_on_commit_callbacks
):
    client = Client(enforce_csrf_checks=True)
    user = UserFactory()

    assert request_reset(client, user.email).status_code == 403
    assert not EmailLog.objects.filter(template_key="password_reset").exists()
    assert client.get(SESSION).status_code == 401
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    with django_capture_on_commit_callbacks(execute=True):
        accepted = request_reset(client, user.email, HTTP_X_CSRFTOKEN=token)

    assert accepted.status_code == 200
    assert len(queued_reset) == 1


def test_reset_submission_requires_browser_csrf(settings):
    client = Client(enforce_csrf_checks=True)
    user = UserFactory()
    original_hash = user.password
    payload = {"key": key_for(user), "password": PASSWORD}

    refused = client.post(RESET, payload, content_type="application/json")
    user.refresh_from_db()
    assert refused.status_code == 403
    assert user.password == original_hash
    assert client.get(SESSION).status_code == 401
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    accepted = client.post(
        RESET, payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )

    assert accepted.status_code == 401
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


@pytest.mark.parametrize(
    ("method", "path"), [("post", REQUEST), ("post", RESET), ("get", RESET)]
)
def test_native_app_client_has_no_reset_endpoints(client, method, path):
    app_path = path.replace("/browser/", "/app/")

    assert getattr(client, method)(app_path).status_code == 404


@pytest.mark.parametrize(
    ("method", "path"), [("GET", REQUEST), ("DELETE", REQUEST), ("PUT", RESET)]
)
def test_reset_endpoints_refuse_unsupported_methods(client, method, path):
    user = UserFactory()
    original_hash = user.password
    data = json.dumps({"email": user.email, "key": key_for(user), "password": PASSWORD})

    response = client.generic(method, path, data, content_type="application/json")

    assert response.status_code == 405
    assert not EmailLog.objects.filter(template_key="password_reset").exists()
    user.refresh_from_db()
    assert user.password == original_hash


@pytest.mark.parametrize("path", [REQUEST, RESET])
@pytest.mark.parametrize("body", ["{", "[]", "{}"])
def test_reset_endpoints_refuse_malformed_or_incomplete_json(client, path, body):
    response = client.post(path, body, content_type="application/json")

    assert response.status_code == 400
    assert not EmailLog.objects.filter(template_key="password_reset").exists()


@pytest.mark.parametrize(
    ("password", "code"),
    [
        ("Short!42", "password_too_short"),
        ("password", "password_too_common"),
        ("58310704293501", "password_entirely_numeric"),
        ("", "required"),
    ],
)
def test_password_policy_refusal_leaves_the_reset_key_usable(client, password, code):
    user = UserFactory()
    original_hash = user.password
    key = key_for(user)

    response = post_reset(client, key, password)

    assert response.status_code == 400
    assert any(
        error.get("param") == "password" and error.get("code") == code
        for error in response.json()["errors"]
    )
    user.refresh_from_db()
    assert user.password == original_hash
    assert post_reset(client, key).status_code == 401
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_reset_request_rate_limit_uses_normalized_email_and_native_response(
    client, settings, queued_reset, django_capture_on_commit_callbacks
):
    settings.ACCOUNT_RATE_LIMITS = {
        **settings.ACCOUNT_RATE_LIMITS,
        "reset_password": "1/m/key",
    }
    user = UserFactory()

    with django_capture_on_commit_callbacks(execute=True):
        first = request_reset(client, user.email)
        limited = request_reset(client, user.email.upper())

    assert first.status_code == 200
    assert limited.status_code == 429
    assert limited.json() == {"status": 429}
    assert len(queued_reset) == 1


def test_reset_submission_keeps_native_ip_limit_and_does_not_consume_key(
    client, settings
):
    settings.ACCOUNT_RATE_LIMITS = {
        **settings.ACCOUNT_RATE_LIMITS,
        "reset_password_from_key": "1/m/ip",
    }
    target = UserFactory()
    original_hash = target.password

    assert post_reset(client, "invalid-key").status_code == 400
    limited = post_reset(client, key_for(target))

    assert limited.status_code == 429
    assert limited.json() == {"status": 429}
    target.refresh_from_db()
    assert target.password == original_hash
    another_browser = Client(REMOTE_ADDR="192.0.2.2")
    assert post_reset(another_browser, key_for(target)).status_code == 401
    target.refresh_from_db()
    assert target.check_password(PASSWORD)


@pytest.fixture
def reset_events(caplog):
    logger = logging.getLogger("iris")
    logger.addHandler(caplog.handler)
    try:
        yield caplog
    finally:
        logger.removeHandler(caplog.handler)


# BR-NOTIF-002 / SEC-09: transport failure preserves the neutral response and safe diagnostic.
def test_reset_queue_failure_is_indistinguishable_and_records_only_safe_diagnostics(
    client, queued_reset, django_capture_on_commit_callbacks, monkeypatch, reset_events
):
    user = UserFactory()
    private_diagnostic = f"private queue diagnostics for {user.email} {key_for(user)}"

    def unavailable(**kwargs):
        raise RuntimeError(private_diagnostic)

    monkeypatch.setattr(send_email, "defer", unavailable)
    with django_capture_on_commit_callbacks(execute=True):
        known = request_reset(client, user.email)
        unknown = request_reset(client, UNKNOWN_EMAIL)

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"status": 200}
    log = EmailLog.objects.get(template_key="password_reset")
    assert log.user_id == user.pk
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "queue_unavailable"
    assert log.attempts == 0
    records = [
        record
        for record in reset_events.records
        if record.name in {"iris.auth", "iris.notifications"}
    ]
    assert any(
        getattr(record, "event", None) == "email_queue_failed" for record in records
    )
    for record in records:
        raw = repr(vars(record))
        assert "private queue diagnostics" not in raw
        assert user.email not in raw
        assert key_for(user) not in raw
