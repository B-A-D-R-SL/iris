# AI contribution: 50% or more AI-generated
"""A real PostgreSQL race must consume a reset capability only once."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local

import pytest
from allauth.account.forms import UserTokenForm
from django.db import close_old_connections, connections
from django.test import Client

from modules.accounts.tests.factories import UserFactory
from modules.accounts.tests.password_reset.test_flow import key_for, post_reset


@pytest.mark.django_db(transaction=True)
def test_concurrent_reset_requests_cannot_both_consume_one_link(monkeypatch):
    user = UserFactory()
    key = key_for(user)
    ready = Barrier(2, timeout=10)
    threads = local()
    original = UserTokenForm._get_user

    def read_before_password_change(form, uid):
        result = original(form, uid)
        if not getattr(threads, "read", False):
            threads.read = True
            ready.wait()
        return result

    def attempt(index):
        close_old_connections()
        try:
            return index, post_reset(
                Client(), key, f"synthetic-race-password-{index}!"
            ).status_code
        finally:
            connections.close_all()

    monkeypatch.setattr(UserTokenForm, "_get_user", read_before_password_change)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (1, 2)))
    assert sorted(status for _, status in results) == [400, 401]
    user.refresh_from_db()
    for index, status in results:
        assert user.check_password(f"synthetic-race-password-{index}!") is (
            status == 401
        )
