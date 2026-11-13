# AI contribution: 50% or more AI-generated
"""Exact retries and compatibility for previously queued household mail."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from procrastinate.jobs import Job

from adapters.mailer.base import MailerError
from adapters.mailer.fake import get_fake_mailer
from modules.notifications.tasks import (
    DeliveryFailure,
    EmailRetryStrategy,
    deliver_household_status_email,
    send_household_status_email,
)


def job(attempts: int, delays: Any = None) -> Job:
    return Job(
        queue="email",
        lock=None,
        queueing_lock=None,
        task_name="notifications.send_email",
        task_kwargs={} if delays is None else {"retry_delays": delays},
        attempts=attempts,
    )


# rule: BR-NOTIF-001
@pytest.mark.parametrize(
    ("attempt", "seconds"), [(0, 60), (1, 300), (2, 900), (3, None)]
)
def test_exact_three_retry_delays(attempt: int, seconds: int | None) -> None:
    before = timezone.now()
    decision = EmailRetryStrategy().get_retry_decision(
        exception=DeliveryFailure("transport_unavailable"),
        job=job(attempt, [60, 300, 900]),
    )
    if seconds is None:
        assert decision is None
    else:
        assert decision is not None
        assert decision.retry_at is not None
        assert before + timedelta(seconds=seconds) <= decision.retry_at
        assert decision.retry_at <= timezone.now() + timedelta(seconds=seconds)


# rule: BR-NOTIF-001
@pytest.mark.parametrize(
    "exception",
    [ValueError("unexpected"), DeliveryFailure("provider_rejected", retryable=False)],
)
def test_only_controlled_transient_failures_are_retried(exception: Exception) -> None:
    assert (
        EmailRetryStrategy().get_retry_decision(
            exception=exception, job=job(0, [60, 300, 900])
        )
        is None
    )


# rule: BR-NOTIF-001
@pytest.mark.parametrize("delays", ["invalid", [0], [True], [-1]])
def test_invalid_job_retry_policy_never_schedules_an_unsafe_delay(
    delays: object,
) -> None:
    assert (
        EmailRetryStrategy().get_retry_decision(
            exception=DeliveryFailure("transport_unavailable"), job=job(0, delays)
        )
        is None
    )


# rule: BR-NOTIF-001
def test_old_job_retry_decision_uses_snapshot_from_its_safe_failure() -> None:
    before = timezone.now()
    decision = EmailRetryStrategy().get_retry_decision(
        exception=DeliveryFailure("transport_unavailable", retry_delays=[60, 300, 900]),
        job=job(1),
    )
    assert decision is not None
    assert decision.retry_at is not None
    assert before + timedelta(seconds=300) <= decision.retry_at
    assert decision.retry_at <= timezone.now() + timedelta(seconds=300)


@pytest.mark.usefixtures("notification_rules")
def test_legacy_household_job_delivers_through_shared_fake() -> None:
    send_household_status_email(
        "holder@example.test", "Status changed", "Status changed"
    )
    [message] = get_fake_mailer().sent
    assert message == {
        "to": ["holder@example.test"],
        "subject": "Status changed",
        "text": "Status changed",
        "html": None,
    }


# rule: BR-NOTIF-001
@pytest.mark.usefixtures("notification_rules")
def test_legacy_task_attaches_policy_for_the_pure_retry_strategy() -> None:
    get_fake_mailer().error = MailerError("transport_unavailable")
    with pytest.raises(DeliveryFailure) as caught:
        send_household_status_email(
            "holder@example.test", "Status changed", "Status changed"
        )
    assert caught.value.retry_delays == [60, 300, 900]
    assert (
        EmailRetryStrategy().get_retry_decision(exception=caught.value, job=job(0))
        is not None
    )


# rule: BR-NOTIF-001
@pytest.mark.django_db
def test_legacy_task_missing_policy_fails_before_transport() -> None:
    with pytest.raises(
        DeliveryFailure, match="^email_configuration_invalid$"
    ) as caught:
        send_household_status_email(
            "holder@example.test", "Status changed", "Status changed"
        )
    assert caught.value.retryable is False
    assert get_fake_mailer().sent == []


# rule: BR-NOTIF-001
@pytest.mark.parametrize("refused", [False, True])
def test_legacy_transport_failure_enters_the_same_safe_retry_contract(
    refused: bool,
) -> None:
    mailer = get_fake_mailer()
    if refused:
        mailer.result = 0
    else:
        mailer.error = MailerError("transport_unavailable")
    with pytest.raises(DeliveryFailure):
        deliver_household_status_email(
            mailer, "holder@example.test", "Status changed", "Status changed"
        )
