# AI contribution: 50% or more AI-generated
"""Public, transaction-aware interface to the email delivery queue."""

import logging
from collections.abc import Mapping
from functools import partial
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError, transaction
from procrastinate.types import JSONDict

from modules.notifications.models import EmailLog
from modules.notifications.rendering import validate_context
from modules.notifications.tasks import send_email
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.notifications")


def _enqueue(
    email_log_id: str, context: dict[str, str], retry_delays: list[int]
) -> None:
    """The business transaction is committed; queue failure must not undo it."""
    try:
        arguments: JSONDict = {
            "email_log_id": email_log_id,
            "context": {key: value for key, value in context.items()},
            "retry_delays": [delay for delay in retry_delays],
        }
        send_email.configure(lock=f"email:{email_log_id}").defer(**arguments)
    except Exception:  # noqa: BLE001 - contain queue details after commit.
        try:
            EmailLog.objects.filter(pk=email_log_id).update(
                status=EmailLog.Status.FAILED, error="queue_unavailable"
            )
        except DatabaseError:
            # An outage can prevent both the queue insertion and this log update.
            pass
        logger.error("email_queue_failed", extra={"event": "email_queue_failed"})


def send(
    user_or_email: Any, template_key: str, context: Mapping[str, object]
) -> EmailLog:
    """Record a message and enqueue it only after the surrounding commit."""
    values = validate_context(template_key, context)
    is_address = isinstance(user_or_email, str)
    email = user_or_email if is_address else getattr(user_or_email, "email", None)
    if not isinstance(email, str):
        raise TypeError("Email recipient is unavailable")
    validate_email(email)
    preference = (
        context.get("language", "fr")
        if is_address
        else getattr(user_or_email, "preferred_language", "fr")
    )
    language = "en" if preference == "en" else "fr"
    user_id = None if is_address else getattr(user_or_email, "pk", None)
    with transaction.atomic():
        email_log = EmailLog.objects.create(
            to_email=email,
            user_id=user_id,
            template_key=template_key,
            language=language,
        )
        try:
            policy = rule_queries.notification_policy()
        except ValidationError:
            email_log.status = EmailLog.Status.FAILED
            email_log.error = "notification_rules_unavailable"
            email_log.save(update_fields=["status", "error", "updated_at"])
            transaction.on_commit(
                lambda: logger.error(
                    "email_configuration_failed",
                    extra={"event": "email_configuration_failed"},
                )
            )
            return email_log
        transaction.on_commit(
            partial(_enqueue, str(email_log.pk), values, policy["retry_delays_seconds"])
        )
    return email_log


def queue_household_status_email(
    *,
    email: str | None,
    language: str,
    status: str,
    reason: str,
) -> None:
    """US-32 compatibility: counter-only files remain valid; reasons stay in Iris."""
    if email:
        key = {"suspended": "household_suspended", "approved": "household_reactivated"}[
            status
        ]
        send(email, key, {"language": language})
