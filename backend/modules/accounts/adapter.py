# AI contribution: 50% or more AI-generated
import hashlib
import time
from typing import Any

from allauth.account import app_settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.internal import ratelimit
from django.contrib.auth.base_user import AbstractBaseUser
from django.core.cache import cache
from django.db import connection, transaction
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    def authenticate(
        self, request: HttpRequest, **credentials: Any
    ) -> AbstractBaseUser | None:
        key = self._get_login_attempts_cache_key(request, **credentials)
        rate = ratelimit.parse_rates(app_settings.RATE_LIMITS["login_failed"])[0]
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
