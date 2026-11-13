# AI contribution: 50% or more AI-generated
"""Terminal email payload retention uses the real PostgreSQL queue lifecycle."""

from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from django.db import connection
from django.utils import timezone
from procrastinate.contrib.django import app
from procrastinate.jobs import Status

from modules.notifications.models import EmailLog
from modules.notifications.tasks import DeliveryFailure, cleanup_email_jobs, send_email


# rule: BR-NOTIF-004
@pytest.mark.django_db(transaction=True)
def test_cleanup_removes_only_old_terminal_email_jobs_br_notif_004(notification_rules):
    log = EmailLog.objects.create(
        to_email="retention@example.test", template_key="file_approved", language="fr"
    )

    def enqueue(queue="email"):
        return send_email.configure(queue=queue).defer(
            email_log_id=str(log.pk), context={}, retry_delays=[60, 300, 900]
        )

    expired = []
    for status in (Status.SUCCEEDED, Status.FAILED, Status.ABORTED):
        job_id = enqueue()
        async_to_sync(app.job_manager.finish_job_by_id_async)(
            job_id=job_id, status=status, delete_job=False
        )
        expired.append(job_id)
    cancelled = enqueue()
    app.job_manager.cancel_job_by_id(cancelled)
    expired.append(cancelled)
    other_queue = enqueue(queue="unrelated")
    async_to_sync(app.job_manager.finish_job_by_id_async)(
        job_id=other_queue, status=Status.SUCCEEDED, delete_job=False
    )
    pending = enqueue()
    # Only test-owned timestamps are aged. Production uses the supported manager.
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE procrastinate_events SET at = %s WHERE job_id = ANY(%s)",
            [timezone.now() - timedelta(hours=25), [*expired, other_queue, pending]],
        )
    recent = enqueue()
    async_to_sync(app.job_manager.finish_job_by_id_async)(
        job_id=recent, status=Status.FAILED, delete_job=False
    )
    cleanup_email_jobs(0)
    remaining = {job.id for job in app.job_manager.list_jobs()}
    assert not remaining.intersection(expired)
    assert {other_queue, pending, recent} <= remaining
    assert EmailLog.objects.filter(pk=log.pk).exists()


# rule: BR-NOTIF-004
@pytest.mark.django_db
def test_cleanup_missing_policy_raises_only_a_safe_error():
    with pytest.raises(DeliveryFailure, match="^email_cleanup_failed$") as failure:
        cleanup_email_jobs(0)
    assert not failure.value.retryable
