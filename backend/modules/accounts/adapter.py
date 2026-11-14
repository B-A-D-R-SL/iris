# AI contribution: 50% or more AI-generated
import hashlib
import logging
import time
from typing import Any

from allauth.account import app_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.internal import ratelimit
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.http import HttpRequest

from modules.accounts.models import User
from modules.notifications import services as notification_services

logger = logging.getLogger("iris.auth")

_NOTIFICATION_TEMPLATES = {
    "account/email/email_confirmation": (
        "account_confirmation",
        "activate_url",
        "confirmation_url",
    ),
    "account/email/email_confirmation_signup": (
        "account_confirmation",
        "activate_url",
        "confirmation_url",
    ),
    "account/email/password_reset_key": (
        "password_reset",
        "password_reset_url",
        "reset_url",
    ),
}


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """Keep public registration closed until US-02 adds email verification."""
        return False

    def send_mail(
        self, template_prefix: str, email: str, context: dict[str, Any]
    ) -> None:
        """Queue reviewed authentication mail; skip unsupported templates privately."""
        specification = _NOTIFICATION_TEMPLATES.get(template_prefix)
        if specification is None:
            logger.info(
                "authentication_email_skipped",
                extra={"event": "authentication_email_skipped"},
            )
            return
        template_key, source_url, destination_url = specification
        user = context.get("user")
        recipient = (
            user
            if isinstance(user, User) and user.email.casefold() == email.casefold()
            else email
        )
        language = user.preferred_language if isinstance(user, User) else None
        if language not in ("fr", "en"):
            request = context.get("request") or self.request
            requested = getattr(request, "LANGUAGE_CODE", "fr")
            language = "en" if str(requested).lower().split("-")[0] == "en" else "fr"
        url = context.get(source_url)
        notification_services.send(
            recipient,
            template_key,
            {destination_url: url, "language": language},
        )

    def authenticate(
        self, request: HttpRequest, **credentials: Any
    ) -> AbstractBaseUser | None:
        key = self._get_login_attempts_cache_key(request, **credentials)
        rate = next(
            candidate
            for candidate in ratelimit.parse_rates(
                app_settings.RATE_LIMITS["login_failed"]
            )
            if candidate.per == "key"
        )
        cache_key = ratelimit.get_cache_key(
            request, action="login_failed", rate=rate, key=key
        )
        lock_id = int.from_bytes(
            hashlib.sha256(cache_key.encode()).digest()[:8], signed=True
        )
        with transaction.atomic():
            # Serialize this email's attempts across workers, including successful rollbacks.
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
            user = super().authenticate(request, **credentials)
            history = cache.get(cache_key, [])
            if user is None and len(history) >= rate.amount:
                # Start the full cooldown at the fifth failure.
                history = [time.time()] * rate.amount
            if history:
                # DatabaseCache rounds expiration down to whole seconds.
                cache.set(cache_key, history, rate.duration + 1)
            return user

    def pre_authenticate(self, request: HttpRequest, **credentials: Any) -> None:
        """Record lockouts without logging the submitted credentials."""
        try:
            super().pre_authenticate(request, **credentials)
        except ValidationError:
            logger.warning(
                "Sign-in rate limited", extra={"event": "sign_in_rate_limited"}
            )
            raise

    def authentication_failed(self, request: HttpRequest, **credentials: Any) -> None:
        """Record rejected credentials without identifying the account."""
        logger.info("Sign-in failed", extra={"event": "sign_in_failed"})
