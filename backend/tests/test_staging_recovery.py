# AI contribution: 50% or more AI-generated
"""SET-17: abandoned jobs recover without automatically resending ambiguous mail."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from asgiref.sync import async_to_sync
from django.db import DatabaseError, connection
from django.utils import timezone
from procrastinate.contrib.django import app
from procrastinate.jobs import Status

from adapters.mailer.fake import get_fake_mailer
from iris.tasks import StalledJobRecoveryError, recover_stalled_jobs
from modules.notifications.models import EmailLog
from modules.notifications.tasks import (
    cleanup_email_jobs,
    send_email,
    send_household_status_email,
)

pytestmark = pytest.mark.django_db(transaction=True)
DIRECT_CONTEXT: Any = None


def _abandon(job_id):
    # Only test-owned queue rows are changed; no real heartbeat wait is needed.
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE procrastinate_jobs SET status = 'doing', worker_id = NULL WHERE id = %s",
            [job_id],
        )


def _recover():
    # Use the same psycopg connector/JSON decoding as the deployed worker.
    worker_app = app.with_connector(app.connector.get_worker_connector())

    async def recover():
        async with worker_app.open_async():
            context: Any = SimpleNamespace(app=worker_app)
            await recover_stalled_jobs.func(context, 0)

    async_to_sync(recover)()


@pytest.mark.parametrize("state", EmailLog.Status.values)
def test_real_queue_recovery_reconciles_only_sending_and_prevents_duplicates(state):
    accepted = timezone.now() if state == EmailLog.Status.SENT else None
    log = EmailLog.objects.create(
        to_email="fictional@example.test",
        template_key="file_approved",
        language="en",
        status=state,
        sent_at=accepted,
    )
    job_id = send_email.configure(lock=f"email:{log.pk}").defer(
        email_log_id=str(log.pk), context={}, retry_delays=[60, 300, 900]
    )
    _abandon(job_id)
    _recover()
    log.refresh_from_db()
    assert log.status == (
        EmailLog.Status.FAILED if state == EmailLog.Status.SENDING else state
    )
    assert log.error == (
        "delivery_outcome_unknown" if state == EmailLog.Status.SENDING else ""
    )
    assert async_to_sync(app.job_manager.get_job_status_async)(job_id) == Status.TODO
    if state in {EmailLog.Status.SENDING, EmailLog.Status.SENT, EmailLog.Status.FAILED}:
        send_email(DIRECT_CONTEXT, str(log.pk), {}, [60, 300, 900])
        assert get_fake_mailer().sent == []
    else:
        send_email(DIRECT_CONTEXT, str(log.pk), {}, [60, 300, 900])
        assert len(get_fake_mailer().sent) == 1


def test_legacy_email_with_unknown_outcome_is_failed_without_resend():
    job_id = send_household_status_email.defer(
        email="legacy@example.test", subject="Fictional", body="Fictional"
    )
    _abandon(job_id)
    _recover()
    assert async_to_sync(app.job_manager.get_job_status_async)(job_id) == Status.FAILED
    assert get_fake_mailer().sent == []


def test_recovery_keeps_healthy_queued_jobs_untouched():
    log = EmailLog.objects.create(
        to_email="fictional@example.test", template_key="file_approved", language="en"
    )
    job_id = send_email.defer(
        email_log_id=str(log.pk), context={}, retry_delays=[60, 300, 900]
    )
    _recover()
    assert async_to_sync(app.job_manager.get_job_status_async)(job_id) == Status.TODO
    log.refresh_from_db()
    assert log.status == EmailLog.Status.PENDING
    assert log.attempts == 0


def test_reconciliation_failure_does_not_retry_or_expose_private_details():
    job = SimpleNamespace(
        task_name="notifications.send_email",
        task_kwargs={"email_log_id": "private-value"},
    )
    manager = SimpleNamespace(
        get_stalled_jobs=AsyncMock(return_value=[job]), retry_job=AsyncMock()
    )
    context: Any = SimpleNamespace(app=SimpleNamespace(job_manager=manager))
    with (
        patch(
            "iris.tasks.notifications.fail_interrupted_delivery",
            side_effect=DatabaseError("private provider/recipient details"),
        ),
        pytest.raises(StalledJobRecoveryError) as error,
    ):
        async_to_sync(recover_stalled_jobs.func)(context, 0)
    assert str(error.value) == "stalled_job_recovery_failed"
    assert error.value.__suppress_context__ is True
    manager.retry_job.assert_not_awaited()


def test_job_retry_failure_leaves_ambiguous_delivery_terminal():
    log = EmailLog.objects.create(
        to_email="fictional@example.test",
        template_key="file_approved",
        language="en",
        status=EmailLog.Status.SENDING,
    )
    job = SimpleNamespace(
        task_name="notifications.send_email", task_kwargs={"email_log_id": str(log.pk)}
    )
    manager = SimpleNamespace(
        get_stalled_jobs=AsyncMock(return_value=[job]),
        retry_job=AsyncMock(side_effect=DatabaseError("private queue payload")),
    )
    context: Any = SimpleNamespace(app=SimpleNamespace(job_manager=manager))
    with pytest.raises(StalledJobRecoveryError, match="^stalled_job_recovery_failed$"):
        async_to_sync(recover_stalled_jobs.func)(context, 0)
    log.refresh_from_db()
    assert log.status == EmailLog.Status.FAILED
    assert log.error == "delivery_outcome_unknown"


def test_live_worker_heartbeat_keeps_running_email_untouched():
    log = EmailLog.objects.create(
        to_email="fictional@example.test",
        template_key="file_approved",
        language="en",
        status=EmailLog.Status.SENDING,
    )
    job_id = send_email.defer(
        email_log_id=str(log.pk), context={}, retry_delays=[60, 300, 900]
    )
    worker_id = async_to_sync(app.job_manager.register_worker)()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE procrastinate_jobs SET status = 'doing', worker_id = %s WHERE id = %s",
            [worker_id, job_id],
        )
    _recover()
    assert async_to_sync(app.job_manager.get_job_status_async)(job_id) == Status.DOING
    log.refresh_from_db()
    assert log.status == EmailLog.Status.SENDING
    assert log.error == ""


def test_staging_recovery_is_registered_with_periodic_worker_schedule():
    scheduled = [
        task
        for task in app.periodic_registry.periodic_tasks.values()
        if task.task.name == "iris.recover_stalled_jobs"
    ]
    assert len(scheduled) == 1
    assert scheduled[0].cron == "*/10 * * * *"
    assert app.tasks["iris.recover_stalled_jobs"].queue == "maintenance"


def test_other_stalled_maintenance_jobs_can_retry_without_email_changes():
    job_id = cleanup_email_jobs.defer(timestamp=0)
    _abandon(job_id)
    _recover()
    assert async_to_sync(app.job_manager.get_job_status_async)(job_id) == Status.TODO
    assert EmailLog.objects.count() == 0


@pytest.mark.parametrize("value", [None, 123, "not-a-uuid"])
def test_invalid_email_recovery_payload_is_sanitized_and_not_retried(value):
    job = SimpleNamespace(
        task_name="notifications.send_email", task_kwargs={"email_log_id": value}
    )
    manager = SimpleNamespace(
        get_stalled_jobs=AsyncMock(return_value=[job]), retry_job=AsyncMock()
    )
    context: Any = SimpleNamespace(app=SimpleNamespace(job_manager=manager))
    with pytest.raises(StalledJobRecoveryError, match="^stalled_job_recovery_failed$"):
        async_to_sync(recover_stalled_jobs.func)(context, 0)
    manager.retry_job.assert_not_awaited()
