# AI contribution: 50% or more AI-generated
"""Run real production HTTP boundaries against pytest's PostgreSQL database."""

import json
import os
import subprocess
import sys
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from django.conf import settings

PRODUCTION_KEY = (
    "fix04-only-synthetic-configuration-key-abcdefghijklmnopqrstuvwxyz-0123456789"
)
BOOTSTRAP = """
import json, sys
import django
django.setup()
from rest_framework.test import APIClient
from iris.throttling import AnonRateThrottle, UserRateThrottle
clock = {'now': 1000.0}
AnonRateThrottle.timer = staticmethod(lambda: clock['now'])
UserRateThrottle.timer = staticmethod(lambda: clock['now'])
client = APIClient()
"""


def production_api(script: str, *arguments: str, proxies: int = 0) -> Any:
    """Fresh settings avoid cached DRF classes; only the test database is used."""
    database = urlsplit(os.environ["DATABASE_URL"])
    if settings.DATABASES["default"]["NAME"] == unquote(database.path.lstrip("/")):
        raise RuntimeError("Production API tests require an isolated test database.")
    test_url = urlunsplit(
        database._replace(path="/" + quote(settings.DATABASES["default"]["NAME"]))
    )
    result = subprocess.run(
        [sys.executable, "-c", BOOTSTRAP + script, *arguments],
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "iris.settings.production",
            "DJANGO_SECRET_KEY": PRODUCTION_KEY,
            "DJANGO_ALLOWED_HOSTS": "testserver",
            "DATABASE_URL": test_url,
            "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "MAILER_ADAPTER": "smtp",
            "DEFAULT_FROM_EMAIL": "noreply@iris.example",
            "PUBLIC_APP_ORIGIN": "https://iris.example",
            "DRF_ANON_THROTTLE_RATE": "2/min",
            "DRF_USER_THROTTLE_RATE": "3/min",
            "DRF_NUM_PROXIES": str(proxies),
            "ALLAUTH_TRUSTED_PROXY_COUNT": str(proxies),
        },
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)
