# AI contribution: 50% or more AI-generated
"""US-93 (BR-HH-ACCOUNT-004): a resend racing the old link's acceptance.

Acceptance locks the invitation, then the household. A resend must take the
same order, or the two can deadlock and one request fails with a server error.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections

from modules.accounts import services as account_services
from modules.households import account_link_services
from modules.households.tests.linking.helpers import (
    HOLDER_EMAIL,
    PASSWORD,
    approved_walk_in,
)

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.usefixtures("notification_rules"),
]


def test_resend_while_the_old_link_is_accepted_does_not_deadlock(
    staff: Any, settings: Any, monkeypatch: Any
) -> None:
    settings.PUBLIC_APP_ORIGIN = "https://iris.example.test"
    household = approved_walk_in(staff)
    token = account_services.create_invitation(
        HOLDER_EMAIL, "Samira", "Example", "beneficiary", household_id=household.pk
    )
    accepting = Event()
    lock_file = account_link_services._locked_walk_in

    def pause_acceptance(household_id: Any) -> Any:
        # The first caller is the acceptance, holding the invitation row: give
        # the resend time to start before the acceptance locks the file.
        if not accepting.is_set():
            accepting.set()
            time.sleep(1.5)
        return lock_file(household_id)

    monkeypatch.setattr(account_link_services, "_locked_walk_in", pause_acceptance)

    def accept() -> Any:
        try:
            return account_services.accept_invitation(token, PASSWORD)
        finally:
            close_old_connections()

    def resend() -> Any:
        accepting.wait(timeout=10)
        try:
            account_link_services.resend_invitation(household.pk, staff)
        except ValidationError as exc:
            return exc
        finally:
            close_old_connections()
        return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        accepted = pool.submit(accept)
        resent = pool.submit(resend)
        user = accepted.result(timeout=30)
        refusal = resent.result(timeout=30)

    household.refresh_from_db()
    assert household.holder_id == user.pk
    assert isinstance(refusal, ValidationError)
    assert refusal.code == "household_already_linked"
