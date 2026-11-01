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

logger = logging.getLogger("iris.auth")


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """Keep public registration closed until US-02 adds email verification."""
        return False

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
