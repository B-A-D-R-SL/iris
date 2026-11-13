# AI contribution: 50% or more AI-generated

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

import pytest
from django.db import OperationalError, connection, transaction
from django.urls import reverse
from psycopg.errors import DeadlockDetected, LockNotAvailable
from rest_framework.test import APIClient

from modules.households.exceptions import DuplicateLockTimeout
from modules.households.models import Household
from modules.households.services import locked_duplicate_check, submit_walk_in

pytestmark = pytest.mark.django_db(transaction=True)


@contextmanager
def _held_duplicate_locks(household, actor):
    acquired, release = Event(), Event()

    def hold():
        try:
            with locked_duplicate_check(household.pk, actor):
                acquired.set()
                if not release.wait(10):
                    raise TimeoutError("Test did not release duplicate locks")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=1) as pool:
        held = pool.submit(hold)
        try:
            assert acquired.wait(5), "Duplicate locks were not acquired"
            yield
        finally:
            release.set()
            held.result(timeout=5)


def _lock_timeout():
    with connection.cursor() as cursor:
        cursor.execute("SHOW lock_timeout")
        return cursor.fetchone()[0]


def _submit_through_api(household, actor):
    client = APIClient()
    client.force_authenticate(actor)
    return client.post(
        reverse("staff-households-submit", kwargs={"id": household.pk}),
        {},
        format="json",
        HTTP_ACCEPT_LANGUAGE="en",
    )


# rule: BR-DUP-003
@pytest.mark.parametrize("entry", ["service", "api"])
@pytest.mark.parametrize("timeout_ms", [50, 150])
def test_contended_advisory_lock_times_out_without_submission(
    entry, timeout_ms, settings, ready_household_factory, submission_worker, caplog
):
    settings.HOUSEHOLD_DUPLICATE_LOCK_TIMEOUT_MS = timeout_ms
    blocker = ready_household_factory()
    household = ready_household_factory()
    household.members.update(person_key="stale-key")
    before = household.updated_at
    original_timeout = _lock_timeout()
    observed_timeouts = []

    def observe(execute, sql, params, many, context):
        if sql.startswith("SELECT pg_advisory_xact_lock"):
            observed_timeouts.append(_lock_timeout())
        return execute(sql, params, many, context)

    with (
        _held_duplicate_locks(blocker, submission_worker),
        connection.execute_wrapper(observe),
        caplog.at_level(logging.INFO, logger="iris.households"),
    ):
        if entry == "api":
            response = _submit_through_api(household, submission_worker)
            assert response.status_code == 503
            assert response.data == {
                "code": "household_unavailable",
                "message": "Household registration is temporarily unavailable. Please try again.",
                "fields": {},
            }
        else:
            with pytest.raises(DuplicateLockTimeout) as exc:
                submit_walk_in(household.pk, submission_worker)
            assert exc.value.__cause__.__cause__.sqlstate == "55P03"
        assert _lock_timeout() == original_timeout

    assert observed_timeouts and set(observed_timeouts) == {f"{timeout_ms}ms"}
    household.refresh_from_db()
    assert household.updated_at == before
    assert household.status == Household.Status.DRAFT
    assert household.status_reason == ""
    assert household.submitted_at is None
    assert list(household.members.values_list("person_key", flat=True)) == ["stale-key"]
    assert not household.draft_events.exists()
    events = [
        record.event for record in caplog.records if record.name == "iris.households"
    ]
    assert events == ["household_duplicate_lock_timeout"]


# rule: BR-DUP-003
def test_successful_lock_acquisition_restores_outer_transaction_timeout(
    settings, ready_household_factory, submission_worker
):
    settings.HOUSEHOLD_DUPLICATE_LOCK_TIMEOUT_MS = 50
    household = ready_household_factory()
    original_timeout = _lock_timeout()
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('lock_timeout', '2s', true)")
        with locked_duplicate_check(household.pk, submission_worker):
            assert _lock_timeout() == "2s"
        assert _lock_timeout() == "2s"
    assert _lock_timeout() == original_timeout


# rule: BR-DUP-003
@pytest.mark.parametrize("failure", ["advisory", "setup", "duplicate_query"])
def test_unrelated_database_failures_are_not_reported_as_lock_timeouts(
    failure, ready_household_factory, submission_worker, monkeypatch
):
    household = ready_household_factory()
    error = OperationalError("Database failure")

    def fail(*args):
        cause = DeadlockDetected() if failure == "advisory" else LockNotAvailable()
        raise error from cause

    def execute(execute, sql, params, many, context):
        if (
            failure == "advisory" and sql.startswith("SELECT pg_advisory_xact_lock")
        ) or (failure == "setup" and sql.startswith("SELECT set_config")):
            fail()
        return execute(sql, params, many, context)

    if failure == "duplicate_query":
        monkeypatch.setattr(
            "modules.households.services.find_possible_duplicates", fail
        )
    with connection.execute_wrapper(execute), pytest.raises(OperationalError) as exc:
        submit_walk_in(household.pk, submission_worker)
    assert exc.value is error
    household.refresh_from_db()
    assert household.status == Household.Status.DRAFT
    assert not household.draft_events.exists()
