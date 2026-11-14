# AI contribution: 50% or more AI-generated
"""Public, transaction-aware interface to the email delivery queue."""

import logging
from collections.abc import Mapping
from functools import partial
from typing import Any, cast

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError, transaction
from django.utils import timezone
from procrastinate.types import JSONDict

from modules.notifications.models import EmailLog
from modules.notifications.rendering import TEMPLATE_KEYS, validate_context
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
                status=EmailLog.Status.FAILED,
                error="queue_unavailable",
                updated_at=timezone.now(),
            )
        except DatabaseError:
            # An outage can prevent both the queue insertion and this log update.
            logger.error(
                "email_outcome_unavailable",
                extra={"event": "email_outcome_unavailable"},
            )
        logger.error("email_queue_failed", extra={"event": "email_queue_failed"})


def _recipient_snapshot(email: object) -> str:
    """Preserve a DB-safe address exactly; an empty failed snapshot means unavailable."""
    limit = cast(int, EmailLog._meta.get_field("to_email").max_length)
    if (
        not isinstance(email, str)
        or len(email) > limit
        or "\x00" in email
        or any("\ud800" <= character <= "\udfff" for character in email)
    ):
        return ""
    return email


def _language(user_or_email: Any, context: Mapping[str, object]) -> str:
    if isinstance(user_or_email, str):
        preference = (
            context.get("language", "fr") if isinstance(context, Mapping) else "fr"
        )
    else:
        preference = getattr(user_or_email, "preferred_language", "fr")
    return "en" if preference == "en" else "fr"


def _message_values(
    email: object, snapshot: str, template_key: str, context: Mapping[str, object]
) -> tuple[dict[str, str], str]:
    """Operational input/configuration failures are notification outcomes, not raises."""
    if not isinstance(email, str) or email != snapshot:
        return {}, "email_recipient_invalid"
    try:
        validate_email(email)
    except ValidationError:
        return {}, "email_recipient_invalid"
    try:
        return validate_context(template_key, context), ""
    except (ValidationError, ValueError, TypeError, ImproperlyConfigured):
        return {}, "email_configuration_invalid"


def _failed(email_log: EmailLog, code: str) -> EmailLog:
    """Keep failed metadata in the business transaction and report only after commit."""
    email_log.status = EmailLog.Status.FAILED
    email_log.error = code
    email_log.save(update_fields=["status", "error", "updated_at"])
    transaction.on_commit(
        lambda: logger.error(
            "email_configuration_failed", extra={"event": "email_configuration_failed"}
        )
    )
    return email_log


def send(
    user_or_email: Any, template_key: str, context: Mapping[str, object]
) -> EmailLog:
    """Record delivery failures without undoing a valid business action."""
    if not isinstance(template_key, str) or template_key not in TEMPLATE_KEYS:
        raise ValueError("Unknown email template")
    is_address = isinstance(user_or_email, str)
    email = user_or_email if is_address else getattr(user_or_email, "email", None)
    user_id = None if is_address else getattr(user_or_email, "pk", None)
    with transaction.atomic():
        email_log = EmailLog.objects.create(
            to_email=_recipient_snapshot(email),
            user_id=user_id,
            template_key=template_key,
            language=_language(user_or_email, context),
        )
        values, error = _message_values(
            email, email_log.to_email, template_key, context
        )
        if error:
            return _failed(email_log, error)
        try:
            policy = rule_queries.notification_policy()
        except ValidationError:
            return _failed(email_log, "notification_rules_unavailable")
        transaction.on_commit(
            partial(_enqueue, str(email_log.pk), values, policy["retry_delays_seconds"])
        )
    return email_log


def queue_set_password_email(*, email: str, token: str, language: str) -> EmailLog:
    """Queue the US-18 walk-in password link through the shared delivery path.

    A missing or invalid ``PUBLIC_APP_ORIGIN`` is recorded as a failed
    ``EmailLog`` instead of undoing the committed approval.
    """
    origin = getattr(settings, "PUBLIC_APP_ORIGIN", None)
    link = f"{origin.rstrip('/')}/invitation/{token}" if isinstance(origin, str) else ""
    return send(
        email,
        "walk_in_set_password",
        {"language": "en" if language == "en" else "fr", "invitation_url": link},
    )


def queue_household_status_email(
    *,
    email: str | None,
    language: str,
    status: str,
    reason: str,
) -> None:
    """Queue the validated US-32 reason; counter-only files remain valid."""
    if email:
        key = {"suspended": "household_suspended", "approved": "household_reactivated"}[
            status
        ]
        send(email, key, {"language": language, "reason": reason})
