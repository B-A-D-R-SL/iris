# AI contribution: 50% or more AI-generated
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from django.conf import settings
from django.contrib.auth.hashers import identify_hasher
from django.core.cache import cache, caches
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import Client

from modules.accounts.models import User
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db
LOGIN = "/api/auth/browser/v1/auth/login"
SESSION = "/api/auth/browser/v1/auth/session"
PASSWORD = "test-password-424"


@pytest.fixture(autouse=True)
def clear_auth_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user():
    return User.objects.create_user(
        "alice@example.test", PASSWORD, first_name="Alice", last_name="Tremblay"
    )


def login(client, email="alice@example.test", password=PASSWORD):
    return client.post(
        LOGIN, {"email": email, "password": password}, content_type="application/json"
    )


def test_user_creation_and_password_hash(user):
    assert isinstance(user.pk, uuid.UUID)
    assert user.preferred_language == "fr"
    assert user.role == "beneficiary"
    assert user.store is None
    assert user.phone == ""
    assert user.is_active
    assert user.last_login is None
    assert user.created_at <= user.updated_at
    assert identify_hasher(user.password).algorithm == "argon2"
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)
    assert not user.check_password("incorrect")
    assert User.objects.get_by_natural_key("ALICE@EXAMPLE.TEST") == user
    assert set(User.Role.values) == {
        "beneficiary",
        "store_staff",
        "store_manager",
        "intake_worker",
        "admin",
    }


@pytest.mark.parametrize("email", ["alice@example.test", "ALICE@EXAMPLE.TEST"])
def test_email_uniqueness_enforced_in_database(user, email):
    with transaction.atomic(), pytest.raises(IntegrityError):
        User.objects.create(email=email)


def test_manager_normalizes_email_and_requires_it():
    user = User.objects.create_user("ALICE@EXAMPLE.TEST")
    assert user.email == "alice@example.test"
    assert not user.has_usable_password()
    with pytest.raises(ValueError, match="Email"):
        User.objects.create_user("")


def test_superuser_creation():
    user = User.objects.create_superuser("admin@example.test", PASSWORD)
    assert user.is_staff and user.is_superuser
    assert user.role == "admin"
    with pytest.raises(ValueError, match="Superusers"):
        User.objects.create_superuser("invalid@example.test", is_staff=False)


def test_login_creates_session_and_updates_last_login(client, user):
    response = login(client, email="ALICE@EXAMPLE.TEST")
    assert response.status_code == 200
    assert response.json()["meta"]["is_authenticated"] is True
    assert client.session["_auth_user_id"] == str(user.pk)
    user.refresh_from_db()
    assert user.last_login is not None
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["httponly"]
    assert cookie["samesite"] == "Lax"


@pytest.mark.parametrize("role", User.Role.values)
def test_every_role_can_sign_in_and_out_through_the_api(client, user, role):
    user.role = role
    if role in {User.Role.STORE_STAFF, User.Role.STORE_MANAGER}:
        user.store = StoreFactory()
    if role in {User.Role.INTAKE_WORKER, User.Role.ADMIN}:
        user.is_staff = True
    if role == User.Role.ADMIN:
        user.is_superuser = True
    user.save()

    assert client.get("/api/me/").status_code == 401
    assert client.get(SESSION).status_code == 401
    refused = login(client, password="incorrect")
    assert refused.status_code == 400
    assert refused.json()["errors"][0]["code"] == "email_password_mismatch"

    signed_in = login(client)
    assert signed_in.status_code == 200
    assert client.get(SESSION).json()["meta"]["is_authenticated"] is True
    current_user = client.get("/api/me/")
    assert current_user.status_code == 200
    assert current_user.json()["id"] == str(user.pk)
    assert current_user.json()["role"] == role
    assert current_user.json()["store"] == (
        str(user.store_id) if user.store_id else None
    )
    user.refresh_from_db()
    assert user.last_login is not None

    assert client.delete(SESSION).status_code == 401
    assert client.get(SESSION).status_code == 401
    assert client.get("/api/me/").status_code == 401


@pytest.mark.parametrize("language", ["fr", "en"])
def test_incorrect_credentials_have_generic_errors(client, user, language):
    client.defaults["HTTP_ACCEPT_LANGUAGE"] = language
    wrong_password = login(client, password="incorrect")
    unknown_email = login(client, email="unknown@example.test", password="incorrect")
    assert wrong_password.status_code == unknown_email.status_code == 400
    assert wrong_password.json()["errors"] == unknown_email.json()["errors"]
    assert wrong_password.json()["errors"][0]["code"] == "email_password_mismatch"
    assert "_auth_user_id" not in client.session


def test_inactive_user_cannot_login(client, user):
    user.is_active = False
    user.save()
    assert login(client).status_code == 401
    assert "_auth_user_id" not in client.session
    assert client.get("/api/me/").status_code == 401


def test_admin_login_uses_rate_limited_sign_in(client, user):
    user.role = User.Role.ADMIN
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["role", "is_staff", "is_superuser"])

    assert client.get("/admin/login/").status_code == 200
    response = client.post(
        "/admin/login/", {"username": user.email, "password": PASSWORD}
    )
    assert response.status_code == 302
    assert client.get("/admin/").status_code == 200


def test_admin_and_app_sign_in_share_failed_attempts(client, user):
    user.role = User.Role.ADMIN
    user.is_staff = True
    user.is_superuser = True
    user.save(update_fields=["role", "is_staff", "is_superuser"])

    for _ in range(4):
        assert (
            client.post(
                "/admin/login/", {"username": user.email, "password": "incorrect"}
            ).status_code
            == 200
        )
    assert login(client, password="incorrect").status_code == 400
    blocked = client.post(
        "/admin/login/", {"username": user.email, "password": PASSWORD}
    )
    assert blocked.status_code == 200
    assert "_auth_user_id" not in client.session


def test_non_staff_user_cannot_sign_in_to_admin(client, user):
    response = client.post(
        "/admin/login/", {"username": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_lockout_lasts_fifteen_minutes_after_fifth_failure(client, user, monkeypatch):
    now = [time.time()]
    start = now[0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    monkeypatch.setattr(
        "django.core.cache.backends.db.tz_now",
        lambda: datetime.fromtimestamp(now[0], UTC),
    )
    for offset in (0, 120, 240, 360, 480):
        now[0] = start + offset
        assert login(client, password="incorrect").json()["errors"][0]["code"] == (
            "email_password_mismatch"
        )
    for offset in (901, 1379.9):
        now[0] = start + offset
        # Reopen the backend to model another worker using the same database cache.
        caches.close_all()
        blocked = login(Client(), email="ALICE@EXAMPLE.TEST")
        assert blocked.status_code == 400
        assert blocked.json()["errors"][0]["code"] == "too_many_login_attempts"
    now[0] = start + 1380
    assert login(client).status_code == 200


def test_expired_failures_and_successes_do_not_trigger_lockout(
    client, user, monkeypatch
):
    now = [time.time()]
    monkeypatch.setattr(time, "time", lambda: now[0])
    for _ in range(4):
        assert login(client, password="incorrect").status_code == 400
    assert login(client).status_code == 200
    assert client.delete(SESSION).status_code == 401
    now[0] += 901
    assert login(client, password="incorrect").status_code == 400
    assert login(client).status_code == 200


def test_cache_pressure_preserves_lockout_and_cleans_expired_records(
    client, user, monkeypatch
):
    now = [time.time()]
    start = now[0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    monkeypatch.setattr(
        "django.core.cache.backends.db.tz_now",
        lambda: datetime.fromtimestamp(now[0], UTC),
    )
    cache.set("expired", True, timeout=1)
    for _ in range(5):
        assert login(client, password="incorrect").status_code == 400
    now[0] = start + 2
    for index in range(350):
        cache.set(f"capacity-probe:{index:04d}", True, timeout=900)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM accounts_auth_cache WHERE cache_key = %s",
            [cache.make_key("expired")],
        )
        assert cursor.fetchone()[0] == 0
    for offset in (2, 899.9):
        now[0] = start + offset
        blocked = login(Client())
        assert blocked.status_code == 400
        assert blocked.json()["errors"][0]["code"] == "too_many_login_attempts"
    now[0] = start + 900
    assert login(client).status_code == 200


@pytest.mark.django_db(transaction=True)
def test_concurrent_attempts_share_one_lockout(user):
    def attempt(_):
        close_old_connections()
        try:
            return login(Client(), password="incorrect").json()["errors"][0]["code"]
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=6) as workers:
        errors = list(workers.map(attempt, range(6)))
    assert errors.count("email_password_mismatch") == 5
    assert errors.count("too_many_login_attempts") == 1
    assert login(Client()).json()["errors"][0]["code"] == "too_many_login_attempts"


def test_logout_invalidates_session(client, user):
    assert login(client).status_code == 200
    assert client.delete(SESSION).status_code == 401
    assert "_auth_user_id" not in client.session
    assert client.get("/api/me/").status_code == 401


def test_logout_invalidates_the_session_shared_by_browser_tabs(client, user):
    assert login(client).status_code == 200
    other_tab = Client()
    other_tab.cookies.update(client.cookies)
    other_browser = Client()
    assert login(other_browser).status_code == 200
    assert other_tab.get("/api/me/").status_code == 200
    assert other_browser.get("/api/me/").status_code == 200

    assert client.delete(SESSION).status_code == 401
    assert other_tab.get("/api/me/").status_code == 401
    assert other_browser.get("/api/me/").status_code == 200


@pytest.mark.parametrize("role", User.Role.values)
@pytest.mark.parametrize("assigned_store", [False, True])
def test_current_user_has_exact_response(client, user, role, assigned_store):
    user.role = role
    user.preferred_language = "en"
    if assigned_store:
        user.store = StoreFactory()
    user.save()
    client.force_login(user)
    response = client.get("/api/me/")
    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.pk),
        "name": "Alice Tremblay",
        "role": role,
        "store": str(user.store_id) if assigned_store else None,
        "language": "en",
    }
    assert client.patch("/api/me/", {}).status_code == 405


def test_anonymous_current_user_is_unauthorized(client):
    assert client.get("/api/me/").status_code == 401


def test_browser_auth_requires_csrf_and_rotates_token(user):
    client = Client(enforce_csrf_checks=True)
    assert login(client).status_code == 403
    assert client.get(SESSION).status_code == 401
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    response = client.post(
        LOGIN,
        {"email": user.email, "password": PASSWORD},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    rotated_token = client.cookies[settings.CSRF_COOKIE_NAME].value
    assert rotated_token != token
    assert client.delete(SESSION).status_code == 403
    assert client.delete(SESSION, HTTP_X_CSRFTOKEN=token).status_code == 403
    assert client.delete(SESSION, HTTP_X_CSRFTOKEN=rotated_token).status_code == 401
    assert client.get("/api/me/").status_code == 401


def test_secure_session_and_csrf_cookies(user, settings):
    settings.SESSION_COOKIE_SECURE = True
    settings.CSRF_COOKIE_SECURE = True
    client = Client()
    response = login(client)
    assert response.status_code == 200
    assert response.cookies[settings.SESSION_COOKIE_NAME]["secure"]
    assert response.cookies[settings.CSRF_COOKIE_NAME]["secure"]
    assert response.cookies[settings.CSRF_COOKIE_NAME]["samesite"] == "Lax"


def test_database_cache_removes_expired_entries(monkeypatch):
    now = [time.time()]
    monkeypatch.setattr(time, "time", lambda: now[0])
    monkeypatch.setattr(
        "django.core.cache.backends.db.tz_now",
        lambda: datetime.fromtimestamp(now[0], UTC),
    )
    cache.set("expired", "value", timeout=1)
    now[0] += 2
    assert cache.get("expired") is None
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM accounts_auth_cache")
        assert cursor.fetchone()[0] == 0
