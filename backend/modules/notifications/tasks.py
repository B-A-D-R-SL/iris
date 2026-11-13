# AI contribution: 50% or more AI-generated
"""Queued delivery, exact retries and cleanup of temporary email job payloads."""

import logging

from asgiref.sync import async_to_sync
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from procrastinate import BaseRetryStrategy, JobContext, RetryDecision
from procrastinate.contrib.django import app
from procrastinate.jobs import Job

from adapters.mailer.base import Mailer, MailerError
from adapters.mailer.factory import get_mailer
from modules.notifications.models import EmailLog
from modules.notifications.rendering import render
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.notifications")


class DeliveryFailure(MailerError):
    """Only safe error codes cross the task/worker diagnostic boundary."""

    def __init__(
        self,
        code: str,
        *,
        retryable: bool = True,
        retry_delays: list[int] | None = None,
    ) -> None:
        super().__init__(code, retryable=retryable)
        self.retry_delays = retry_delays


class EmailRetryStrategy(BaseRetryStrategy):
    """BR-NOTIF-001: use the policy captured in the queued job."""

    def get_retry_decision(
        self, *, exception: BaseException, job: Job
    ) -> RetryDecision | None:
        delays: object = job.task_kwargs.get("retry_delays")
        if not isinstance(exception, DeliveryFailure) or not exception.retryable:
            return None
        if delays is None:
            # Legacy tasks load this in their synchronous body. Retry decisions
            # run on the worker event loop and must never issue synchronous ORM work.
            delays = exception.retry_delays
        if not isinstance(delays, list) or job.attempts >= len(delays):
            return None
        delay = delays[job.attempts]
        if type(delay) is not int or delay <= 0:
            return None
        return RetryDecision(retry_in={"seconds": delay})


def _failure(
    email_log: EmailLog,
    code: str,
    *,
    retryable: bool,
    retries: int,
    job_attempts: int | None = None,
) -> None:
    attempts = email_log.attempts - 1 if job_attempts is None else job_attempts
    will_retry = retryable and attempts < retries
    EmailLog.objects.filter(pk=email_log.pk).update(
        status=EmailLog.Status.RETRYING if will_retry else EmailLog.Status.FAILED,
        error=code,
        updated_at=timezone.now(),
    )
    event = "email_retry_scheduled" if will_retry else "email_send_failed"
    logger.warning(event, extra={"event": event})


def _deliver(
    email_log_id: str,
    context: dict[str, str],
    retry_delays: list[int],
    job_attempts: int | None,
) -> None:
    # Per-log queue locks serialize duplicate jobs; network calls never hold DB locks.
    with transaction.atomic():
        email_log = EmailLog.objects.select_for_update().filter(pk=email_log_id).first()
        if email_log is None or email_log.status in {
            EmailLog.Status.SENT,
            EmailLog.Status.FAILED,
        }:
            return
        try:
            message = render(email_log.template_key, email_log.language, context)
            mailer = get_mailer()
        except Exception:  # noqa: BLE001 - configuration exceptions may contain context.
            _failure(
                email_log,
                "email_configuration_invalid",
                retryable=False,
                retries=0,
                job_attempts=job_attempts,
            )
            message = None
        if message is not None:
            EmailLog.objects.filter(pk=email_log.pk).update(
                status=EmailLog.Status.SENDING,
                attempts=F("attempts") + 1,
                error="",
                updated_at=timezone.now(),
            )
            email_log.attempts += 1
    if message is None:
        raise DeliveryFailure("email_configuration_invalid", retryable=False)
    try:
        if (
            mailer.send(
                [email_log.to_email],
                message.subject,
                html=message.html,
                text=message.text,
            )
            != 1
        ):
            raise MailerError("provider_rejected")
    except MailerError as exc:
        _failure(
            email_log,
            exc.code,
            retryable=exc.retryable,
            retries=len(retry_delays),
            job_attempts=job_attempts,
        )
        raise DeliveryFailure(exc.code, retryable=exc.retryable) from None
    except Exception:  # noqa: BLE001 - normalize even unexpected transport failures.
        _failure(
            email_log,
            "transport_unavailable",
            retryable=True,
            retries=len(retry_delays),
            job_attempts=job_attempts,
        )
        raise DeliveryFailure("transport_unavailable") from None
    EmailLog.objects.filter(pk=email_log.pk).update(
        status=EmailLog.Status.SENT,
        error="",
        sent_at=timezone.now(),
        updated_at=timezone.now(),
    )
    logger.info("email_sent", extra={"event": "email_sent"})


@app.task(
    name="notifications.send_email",
    queue="email",
    retry=EmailRetryStrategy(),
    pass_context=True,
)
def send_email(
    job_context: JobContext | None,
    email_log_id: str,
    context: dict[str, str],
    retry_delays: list[int],
) -> None:
    """Render and deliver; sanitized failures escape so Procrastinate can retry."""
    try:
        _deliver(
            email_log_id,
            context,
            retry_delays,
            job_context.job.attempts if job_context else None,
        )
    except DeliveryFailure:
        raise
    except Exception:  # noqa: BLE001 - database diagnostics must not expose payloads.
        try:
            EmailLog.objects.filter(pk=email_log_id).exclude(
                status=EmailLog.Status.SENT
            ).update(
                status=EmailLog.Status.RETRYING
                if job_context is None or job_context.job.attempts < len(retry_delays)
                else EmailLog.Status.FAILED,
                error="delivery_unavailable",
                updated_at=timezone.now(),
            )
        except Exception:  # noqa: BLE001 - a database outage also prevents reconciliation.
            logger.error(
                "email_outcome_unavailable",
                extra={"event": "email_outcome_unavailable"},
            )
        raise DeliveryFailure("delivery_unavailable") from None


def deliver_household_status_email(
    mailer: Mailer, email: str, subject: str, body: str
) -> None:
    """Compatibility for jobs already queued with the old argument shape."""
    try:
        if mailer.send([email], subject, text=body) != 1:
            raise MailerError("provider_rejected")
    except MailerError as exc:
        raise DeliveryFailure(exc.code, retryable=exc.retryable) from None
    except Exception:  # noqa: BLE001 - sanitize diagnostics from legacy jobs too.
        raise DeliveryFailure("transport_unavailable") from None


@app.task(
    name="notifications.send_household_status_email",
    queue="email",
    retry=EmailRetryStrategy(),
)
def send_household_status_email(email: str, subject: str, body: str) -> None:
    """Compatibility only; new callers use the templated send service."""
    try:
        delays = rule_queries.notification_policy()["retry_delays_seconds"]
    except Exception:  # noqa: BLE001 - only safe configuration failures reach diagnostics.
        raise DeliveryFailure("email_configuration_invalid", retryable=False) from None
    try:
        deliver_household_status_email(get_mailer(), email, subject, body)
    except DeliveryFailure as exc:
        raise DeliveryFailure(
            exc.code, retryable=exc.retryable, retry_delays=delays
        ) from None


@app.periodic(cron="0 * * * *")
@app.task(name="notifications.cleanup_email_jobs", queue="maintenance")
def cleanup_email_jobs(timestamp: int) -> None:
    """BR-NOTIF-004: purge terminal job payloads while retaining EmailLog metadata."""
    try:
        policy = rule_queries.notification_policy()
        async_to_sync(app.job_manager.delete_old_jobs)(
            nb_hours=policy["job_retention_hours"],
            queue="email",
            include_failed=True,
            include_cancelled=True,
            include_aborted=True,
        )
    except Exception:  # noqa: BLE001 - queue cleanup errors may contain job arguments.
        logger.error("email_cleanup_failed", extra={"event": "email_cleanup_failed"})
        raise DeliveryFailure("email_cleanup_failed", retryable=False) from None
