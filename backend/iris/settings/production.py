# AI contribution: 50% or more AI-generated
"""Production settings for Iris."""

import re

from django.core.exceptions import ImproperlyConfigured

from .base import *
from .base import (
    DATABASES,
    MAILERS,
    REST_FRAMEWORK,
    SECRET_KEY,
    SPECTACULAR_SETTINGS,
    env,
)

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be configured in production.")

if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(("django-insecure", "iris-insecure")):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must contain at least 50 characters and must not use "
        "a development prefix in production."
    )

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires a PostgreSQL DATABASE_URL.")

if REST_FRAMEWORK["NUM_PROXIES"] < 0:
    raise ImproperlyConfigured("DRF_NUM_PROXIES must be zero or positive.")

if MAILERS["default"]["BACKEND"] in {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
}:
    raise ImproperlyConfigured(
        "EMAIL_BACKEND must deliver email in production; console, dummy, file-based "
        "and in-memory backends are forbidden."
    )

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# Browser preload enrollment needs the domain owner's approval. Keep regular
# HSTS active while acknowledging only Django's preload opt-in warning.
SECURE_HSTS_PRELOAD = False
SILENCED_SYSTEM_CHECKS = ["security.W021"]
# Deployment must strip client-supplied headers and set this at its trusted proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


def _throttle_rate(name: str, default: str) -> str:
    """Reject disabled or malformed deployment limits before serving requests."""
    rate: str = env(name, default=default)
    if not re.fullmatch(
        r"[1-9][0-9]*/(?:s|secs?|seconds?|m|mins?|minutes?|h|hrs?|hours?|d|days?)",
        rate,
    ):
        raise ImproperlyConfigured(
            f"{name} must be a positive request count per second, minute, hour or day."
        )
    return rate


REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [
        "iris.throttling.AnonRateThrottle",
        "iris.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
        "anon": _throttle_rate("DRF_ANON_THROTTLE_RATE", "60/min"),
        "user": _throttle_rate("DRF_USER_THROTTLE_RATE", "300/min"),
    },
}
SPECTACULAR_SETTINGS = {
    **SPECTACULAR_SETTINGS,
    "SERVE_PERMISSIONS": ["iris.api.IsActiveAdmin"],
}
