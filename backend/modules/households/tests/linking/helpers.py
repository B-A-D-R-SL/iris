# AI contribution: 50% or more AI-generated
"""Approved walk-in files and accounts for the US-93 link and resend tests."""

import time
from typing import Any

from django.db import connection

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household
from modules.households.tests.approval.helpers import NOW
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.stores.tests.factories import StoreFactory

HOLDER_EMAIL = "holder@example.test"
PASSWORD = "Uncommon-secret-9146!"


def approved_walk_in(staff: Any, **kwargs: Any) -> Any:
    """An approved walk-in file with an email and a holder member, not linked."""
    values: dict[str, Any] = {
        "created_by": staff,
        "status": Household.Status.APPROVED,
        "email": HOLDER_EMAIL,
        "approved_at": NOW,
        "expires_at": NOW.replace(year=NOW.year + 1),
    }
    household = HouseholdFactory(**(values | kwargs))
    MemberFactory(
        household=household,
        relation="holder",
        first_name="Samira",
        last_name="Example",
    )
    return household


def account(role: str = "beneficiary", **kwargs: Any) -> Any:
    """An account using the file's email; store roles get the store they need."""
    if role in ("store_staff", "store_manager"):
        kwargs.setdefault("store", StoreFactory())
    values = {"email": HOLDER_EMAIL, "first_name": "Samira", "last_name": "Example"}
    return UserFactory(role=role, **(values | kwargs))


def backend_pid() -> int:
    """The ID of this thread's PostgreSQL connection."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_backend_pid()")
        return int(cursor.fetchone()[0])


def until_blocked_by_this_connection(other: list[int]) -> None:
    """Return once the other thread's connection waits on a lock this one holds.

    The other thread puts its `backend_pid()` in `other`. pg_blocking_pids names
    only the connections blocking it, so lock waits elsewhere are ignored.
    """
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not other:
            continue
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_backend_pid() = ANY(pg_blocking_pids(%s))", [other[0]]
            )
            if cursor.fetchone()[0]:
                return
    raise AssertionError("The other request never waited for this one's lock.")
