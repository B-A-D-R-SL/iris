# AI contribution: 50% or more AI-generated
"""Check that shared keys stay locked until commit or rollback."""

from concurrent.futures import ThreadPoolExecutor
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


# rule: BR-DUP-003
@pytest.mark.parametrize("match", ["address", "person", "reversed_people"])
@pytest.mark.parametrize("commit_first", [True, False], ids=["commit", "rollback"])
def test_overlapping_submissions_wait_for_outer_transaction_before_checking(
    match, commit_first, ready_household_factory, submission_worker
):
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

    first_saved = Event()
    second_connected = Event()
    second_finished = Event()
    release_first = Event()
    second_session = []

    def submit_first():
        try:
            with transaction.atomic():
                result = submit_walk_in(first.pk, submission_worker)
                first_saved.set()
                if not release_first.wait(timeout=10):
                    raise TimeoutError("Test did not release the first submission")
                if not commit_first:
                    raise AbortSubmission
                return result.status
        except AbortSubmission:
            return "rolled_back"
        finally:
            connection.close()

    def submit_second():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout = '8s'")
                cursor.execute("SELECT pg_backend_pid()")
                second_session.append(cursor.fetchone()[0])
            second_connected.set()
            return submit_walk_in(second.pk, submission_worker).status
        finally:
            second_finished.set()
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        first_result = workers.submit(submit_first)
        try:
            assert first_saved.wait(timeout=5), (
                "First submission did not reach its save"
            )
            second_result = workers.submit(submit_second)
            assert second_connected.wait(timeout=5)
            deadline = monotonic() + 5
            waiting = False
            while monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM pg_locks "
                        "WHERE pid = %s AND locktype = 'advisory' AND NOT granted)",
                        [second_session[0]],
                    )
                    waiting = cursor.fetchone()[0]
                if waiting or second_result.done():
                    break
                if second_finished.wait(timeout=0.01):
                    break
            assert waiting, (
                "Second submission must wait on a real PostgreSQL advisory lock"
            )
            assert not second_result.done()
            # The other connection cannot see changes before commit.
            first.refresh_from_db()
            second.refresh_from_db()
            assert first.status == second.status == Household.Status.DRAFT
        finally:
            release_first.set()
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
