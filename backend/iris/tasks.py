# AI contribution: 50% or more AI-generated
"""Recover abandoned jobs when the shared staging worker is forcibly terminated."""

import logging

from asgiref.sync import sync_to_async
from procrastinate import JobContext
from procrastinate.contrib.django import app
from procrastinate.jobs import Status

from modules.notifications import services as notifications

logger = logging.getLogger("iris.deployment")


class StalledJobRecoveryError(RuntimeError):
    """Queue internals and email payloads must not escape recovery diagnostics."""


# Infrastructure heartbeat recovery cadence, not a notification retry RuleSet.
@app.periodic(cron="*/10 * * * *")
@app.task(
    name="iris.recover_stalled_jobs",
    queue="maintenance",
    queueing_lock="iris.recover_stalled_jobs",
    pass_context=True,
)
async def recover_stalled_jobs(context: JobContext, timestamp: int) -> None:
    """Use dead-worker heartbeats; never infer abandonment from job duration."""
    try:
        manager = context.app.job_manager
        for job in await manager.get_stalled_jobs():
            if job.task_name == "notifications.send_household_status_email":
                # Legacy payloads have no EmailLog to reconcile; avoid blind resends.
                await manager.finish_job(job, status=Status.FAILED, delete_job=False)
            else:
                if job.task_name == "notifications.send_email":
                    await sync_to_async(notifications.fail_interrupted_delivery)(
                        job.task_kwargs.get("email_log_id")
                    )
                await manager.retry_job(job)
            logger.info(
                "stalled_job_recovered", extra={"event": "stalled_job_recovered"}
            )
    except Exception:  # noqa: BLE001 - queue errors can contain private task payloads.
        logger.error(
            "stalled_job_recovery_failed",
            extra={"event": "stalled_job_recovery_failed"},
        )
        raise StalledJobRecoveryError("stalled_job_recovery_failed") from None
