# AI contribution: 50% or more AI-generated
"""Recovery must contain delivery failures and emit only safe committed events."""

import logging

import pytest
from django.db import DatabaseError

from modules.accounts.tests.factories import UserFactory
from modules.accounts.tests.password_reset.test_flow import REQUEST, key_for, post_reset

pytestmark = pytest.mark.django_db


@pytest.fixture
def auth_records(caplog):
    logger = logging.getLogger("iris.auth")
    original = logger.propagate
    logger.propagate = False
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger=logger.name):
            yield caplog
    finally:
        logger.removeHandler(caplog.handler)
        logger.propagate = original


def test_notification_database_failure_keeps_the_neutral_request_response(
    client, monkeypatch, auth_records
):
    user = UserFactory()
    secret = f"sensitive-exception-{user.email}"

    def unavailable(*args, **kwargs):
        raise DatabaseError(secret)

    monkeypatch.setattr(
        "modules.accounts.adapter.notification_services.send", unavailable
    )
    known = client.post(REQUEST, {"email": user.email}, content_type="application/json")
    unknown = client.post(
        REQUEST, {"email": "unregistered@example.test"}, content_type="application/json"
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json() == {"status": 200}
    [record] = [
        r
        for r in auth_records.records
        if getattr(r, "event", "") == "password_reset_email_unavailable"
    ]
    assert record.levelno == logging.ERROR
    assert secret not in str(vars(record))
    assert record.exc_info is None


def test_successful_reset_logs_after_commit_without_credentials(
    client, auth_records, django_capture_on_commit_callbacks
):
    user = UserFactory()
    key = key_for(user)
    with django_capture_on_commit_callbacks(execute=True):
        assert post_reset(client, key).status_code == 401
        assert not [
            r
            for r in auth_records.records
            if getattr(r, "event", "") == "password_reset_completed"
        ]
    [record] = [
        r
        for r in auth_records.records
        if getattr(r, "event", "") == "password_reset_completed"
    ]
    assert record.levelno == logging.INFO
    assert record.args == () and record.exc_info is None
    for secret in (user.email, str(user.pk), key):
        assert secret not in str(vars(record))
