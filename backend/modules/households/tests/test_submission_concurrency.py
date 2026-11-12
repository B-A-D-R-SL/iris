# AI contribution: 50% or more AI-generated
"""Check that shared keys stay locked until commit or rollback."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Event
from time import monotonic

import pytest
from django.db import connection, transaction

from modules.households.models import Household, Member
from modules.households.services import submit_walk_in
from modules.households.tests.factories import MemberFactory

pytestmark = pytest.mark.django_db(transaction=True)


class AbortSubmission(Exception):
    """Roll back the first submission."""


@dataclass
class SubmissionSync:
    """Coordinate two database connections without fixed sleeps."""

    first_saved: Event = field(default_factory=Event)
    second_connected: Event = field(default_factory=Event)
    second_finished: Event = field(default_factory=Event)
    release_first: Event = field(default_factory=Event)
    second_pid: int | None = None


def _overlapping_households(match, ready_household_factory):
    first = ready_household_factory(first_name="Alpha")
    second = ready_household_factory(
        first_name="Alpha" if match == "person" else "Bravo",
        street_number="100" if match == "address" else "200",
    )
    if match == "reversed_people":
        for household, name in ((first, "Bravo"), (second, "Alpha")):
            MemberFactory(
                household=household,
                first_name=name,
                last_name="Holder",
                date_of_birth="1990-01-01",
                relation=Member.Relation.CHILD,
            )
    return first, second


def _submit_first(household_id, worker, sync, commit_first):
    """Keep the first transaction open until the test releases it."""
    try:
        with transaction.atomic():
            result = submit_walk_in(household_id, worker)
            sync.first_saved.set()
            if not sync.release_first.wait(timeout=10):
                raise TimeoutError("Test did not release the first submission")
            if not commit_first:
                raise AbortSubmission
            return result.status
    except AbortSubmission:
        return "rolled_back"
    finally:
        connection.close()


def _submit_second(household_id, worker, sync):
    """Expose the second connection's PID so the test can inspect its lock."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET lock_timeout = '8s'")
            cursor.execute("SELECT pg_backend_pid()")
            sync.second_pid = cursor.fetchone()[0]
        sync.second_connected.set()
        return submit_walk_in(household_id, worker).status
    finally:
        sync.second_finished.set()
        connection.close()


def _assert_waiting_on_lock(sync, second_result):
    """Check PostgreSQL's lock table while the first transaction stays open."""
    assert sync.second_connected.wait(timeout=5)
    deadline = monotonic() + 5
    waiting = False
    while monotonic() < deadline:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_locks "
                "WHERE pid = %s AND locktype = 'advisory' AND NOT granted)",
                [sync.second_pid],
            )
            waiting = cursor.fetchone()[0]
        if waiting or second_result.done() or sync.second_finished.wait(timeout=0.01):
            break
    assert waiting, "Second submission must wait on a PostgreSQL advisory lock"
    assert not second_result.done()


# rule: BR-DUP-003
@pytest.mark.parametrize("match", ["address", "person", "reversed_people"])
@pytest.mark.parametrize("commit_first", [True, False], ids=["commit", "rollback"])
def test_overlapping_submissions_wait_for_outer_transaction_before_checking(
    match, commit_first, ready_household_factory, submission_worker
):
    """Only committed submissions can cause the waiting file to enter review."""
    first, second = _overlapping_households(match, ready_household_factory)
    sync = SubmissionSync()
    with ThreadPoolExecutor(max_workers=2) as workers:
        first_result = workers.submit(
            _submit_first, first.pk, submission_worker, sync, commit_first
        )
        try:
            assert sync.first_saved.wait(timeout=5), (
                "First submission did not reach its save"
            )
            second_result = workers.submit(
                _submit_second, second.pk, submission_worker, sync
            )
            _assert_waiting_on_lock(sync, second_result)
            first.refresh_from_db()
            second.refresh_from_db()
            assert first.status == second.status == Household.Status.DRAFT
        finally:
            sync.release_first.set()
        assert first_result.result(timeout=10) == (
            Household.Status.SUBMITTED if commit_first else "rolled_back"
        )
        assert second_result.result(timeout=10) == (
            Household.Status.REVIEW_REQUIRED
            if commit_first
            else Household.Status.SUBMITTED
        )

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.status_reason == ""
    assert second.status_reason == ("POSSIBLE_DUPLICATE" if commit_first else "")
    assert (first.submitted_at is not None) is commit_first
    assert second.submitted_at is not None
    assert Household.objects.count() == 2
