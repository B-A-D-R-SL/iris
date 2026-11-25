# AI contribution: 50% or more AI-generated
"""US-93 (BR-HH-ACCOUNT-002): a counter link racing a change to the account.

The link checks the account's role and activation, then saves the holder. The
account row stays locked in between, so a change committed meanwhile is seen.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction

from modules.households.account_link_services import link_existing_account
from modules.households.tests.linking.helpers import (
    account,
    approved_walk_in,
    backend_pid,
    until_blocked_by_this_connection,
)

pytestmark = pytest.mark.django_db(transaction=True)
# Through Django: households code never imports the accounts models.
User = get_user_model()


# rule: BR-HH-ACCOUNT-002
def test_account_deactivated_while_being_linked_is_refused(staff: Any) -> None:
    household = approved_walk_in(staff)
    user = account()
    deactivating = Event()
    linker: list[int] = []

    def deactivate() -> None:
        # An admin holds the account row while deactivating it.
        try:
            with transaction.atomic():
                User.objects.select_for_update().get(pk=user.pk)
                deactivating.set()
                until_blocked_by_this_connection(linker)
                User.objects.filter(pk=user.pk).update(is_active=False)
        finally:
            connection.close()

    def link() -> Any:
        deactivating.wait(timeout=10)
        try:
            linker.append(backend_pid())
            link_existing_account(household.pk, staff)
        except ValidationError as exc:
            return exc
        finally:
            connection.close()
        return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        admin = pool.submit(deactivate)
        linking = pool.submit(link)
        admin.result(timeout=30)
        refusal = linking.result(timeout=30)

    household.refresh_from_db()
    assert household.holder_id is None
    assert isinstance(refusal, ValidationError)
    assert refusal.code == "inactive"
