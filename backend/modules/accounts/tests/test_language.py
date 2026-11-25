# AI contribution: 50% or more AI-generated
"""US-08: a signed-in user saves French or English on their account."""

import json
import logging
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from rest_framework.test import APIClient

from iris.observability import JsonLogFormatter
from modules.accounts import services
from modules.accounts.models import User
from modules.accounts.roles import UserRole
from modules.accounts.tests.factories import UserFactory
from modules.notifications import services as notification_services
from modules.stores.tests.factories import StoreFactory

pytestmark = pytest.mark.django_db
ME = "/api/me/"
STORE_ROLES = (UserRole.STORE_STAFF, UserRole.STORE_MANAGER)


def make_user(role: str = UserRole.BENEFICIARY, **kwargs: Any) -> Any:
    if role in STORE_ROLES:
        kwargs.setdefault("store", StoreFactory())
    return UserFactory(role=role, **kwargs)


def patch(user: Any, body: Any, language: str = "en") -> Any:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client.patch(ME, body, format="json", HTTP_ACCEPT_LANGUAGE=language)


def saved_language(user: Any) -> str:
    return User.objects.values_list("preferred_language", flat=True).get(pk=user.pk)


# rule: BR-LANG-002
@pytest.mark.parametrize("role", UserRole.values)
def test_every_role_saves_its_language_through_the_api_and_database(role: str) -> None:
    user = make_user(role)
    response = patch(user, {"language": "en"})
    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.pk),
        "name": user.get_full_name(),
        "role": role,
        "store": str(user.store_id) if user.store_id else None,
        "language": "en",
    }
    assert saved_language(user) == "en"

    assert patch(user, {"language": "fr"}).json()["language"] == "fr"
    assert saved_language(user) == "fr"


# rule: BR-LANG-002
def test_anonymous_visitors_cannot_change_a_language() -> None:
    response = patch(None, {"language": "en"})
    assert response.status_code in (401, 403)
    assert response.json()["code"] == "not_authenticated"


# rule: BR-LANG-002
def test_a_browser_session_must_send_the_csrf_token() -> None:
    user = make_user()
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    response = client.patch(
        ME, json.dumps({"language": "en"}), content_type="application/json"
    )
    assert response.status_code == 403
    assert saved_language(user) == "fr"


# rule: BR-LANG-002
@pytest.mark.parametrize(
    ("language", "message"),
    [
        ("en", "Choose French or English."),
        ("fr", "Choisissez le français ou l'anglais."),
    ],
)
@pytest.mark.parametrize("value", ["de", "EN", "", None, 1])
def test_only_french_or_english_is_accepted(
    value: Any, language: str, message: str
) -> None:
    user = make_user(preferred_language="en")
    response = patch(user, {"language": value}, language)
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert list(body["fields"]) == ["language"]
    if value not in ("", None):
        assert body["fields"]["language"] == [message]
    assert saved_language(user) == "en"


# rule: BR-LANG-002
def test_the_language_is_required() -> None:
    user = make_user()
    response = patch(user, {})
    assert response.status_code == 400
    assert list(response.json()["fields"]) == ["language"]


# rule: BR-LANG-002
def test_other_account_fields_are_refused_and_nothing_changes() -> None:
    user = make_user()
    response = patch(
        user, {"language": "en", "role": "admin", "email": "other@example.test"}
    )
    assert response.status_code == 400
    assert sorted(response.json()["fields"]) == ["email", "role"]
    user.refresh_from_db()
    assert (user.preferred_language, user.role) == ("fr", UserRole.BENEFICIARY)
    assert user.email != "other@example.test"


# rule: BR-LANG-002
def test_the_service_refuses_an_unsupported_language() -> None:
    user = make_user()
    with pytest.raises(ValidationError) as caught:
        services.change_language(user, "es")
    assert caught.value.code == "invalid_language"
    assert saved_language(user) == "fr"


# rule: BR-LANG-002
def test_each_change_is_logged_without_personal_data(
    caplog: pytest.LogCaptureFixture, django_capture_on_commit_callbacks: Any
) -> None:
    user = make_user()
    with (
        caplog.at_level(logging.INFO, logger="iris.accounts"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        services.change_language(user, "en")
    [record] = [r for r in caplog.records if r.getMessage() == "language_changed"]
    line = JsonLogFormatter().format(record)
    assert json.loads(line)["event"] == "language_changed"
    for private in (str(user.pk), user.email, user.first_name, user.last_name):
        assert private not in line


# rule: BR-LANG-002
def test_the_signal_is_sent_even_when_the_language_is_unchanged() -> None:
    user = make_user(preferred_language="en")
    received: list[str] = []

    def receiver(*, language: str, **kwargs: Any) -> None:
        received.append(language)

    services.language_changed.connect(receiver)
    try:
        services.change_language(user, "en")
    finally:
        services.language_changed.disconnect(receiver)
    assert received == ["en"]


# rule: BR-LANG-002
def test_a_stale_account_instance_still_saves_the_requested_language() -> None:
    # Another request saved "en" after this one loaded the account as "fr".
    stale = make_user(preferred_language="fr")
    type(stale).objects.filter(pk=stale.pk).update(preferred_language="en")

    saved = services.change_language(stale, "fr")

    assert saved is stale
    assert saved.preferred_language == "fr"
    stale.refresh_from_db()
    assert stale.preferred_language == "fr"


# rule: BR-LANG-003, BR-NOTIF-003
@pytest.mark.usefixtures("notification_rules")
def test_emails_after_the_change_use_the_saved_language() -> None:
    user = make_user()
    assert notification_services.send(user, "file_approved", {}).language == "fr"
    assert patch(user, {"language": "en"}).status_code == 200
    user.refresh_from_db()
    assert notification_services.send(user, "file_approved", {}).language == "en"
