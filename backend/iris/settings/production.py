# AI contribution: 50% or more AI-generated
"""Production settings for Iris."""

import re
from ipaddress import ip_address
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import validate_email

from .base import *
from .base import (
    AZURE_COMMUNICATION_CONNECTION_STRING,
    DATABASES,
    DEFAULT_FROM_EMAIL,
    MAILER_ADAPTER,
    MAILERS,
    PUBLIC_APP_ORIGIN,
    REST_FRAMEWORK,
    SECRET_KEY,
    SPECTACULAR_SETTINGS,
    env,
)

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be configured in production.")

if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must not contain '*' in production."
    )

if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(("django-insecure", "iris-insecure")):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must contain at least 50 characters and must not use "
        "a development prefix in production."
    )

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires a PostgreSQL DATABASE_URL.")

if REST_FRAMEWORK["NUM_PROXIES"] < 0:
    raise ImproperlyConfigured("DRF_NUM_PROXIES must be zero or positive.")

# Allauth's sign-in quotas select client IPs independently of DRF.
ALLAUTH_TRUSTED_PROXY_COUNT = env.int("ALLAUTH_TRUSTED_PROXY_COUNT", default=0)
if ALLAUTH_TRUSTED_PROXY_COUNT < 0:
    raise ImproperlyConfigured("ALLAUTH_TRUSTED_PROXY_COUNT must be zero or positive.")

if MAILER_ADAPTER == "fake":
    raise ImproperlyConfigured("MAILER_ADAPTER must deliver email in production.")

if MAILER_ADAPTER == "smtp" and MAILERS["default"]["BACKEND"] in {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
}:
    raise ImproperlyConfigured(
        "EMAIL_BACKEND must deliver email in production; console, dummy, file-based "
        "and in-memory backends are forbidden."
    )

try:
    validate_email(DEFAULT_FROM_EMAIL)
except ValidationError:
    raise ImproperlyConfigured(
        "DEFAULT_FROM_EMAIL must be a valid sender address in production."
    ) from None
if DEFAULT_FROM_EMAIL.rsplit("@", 1)[-1].lower().endswith((".local", ".localhost")):
    raise ImproperlyConfigured(
        "DEFAULT_FROM_EMAIL must be a public sender address in production."
    )

if MAILER_ADAPTER == "azure" and not AZURE_COMMUNICATION_CONNECTION_STRING:
    raise ImproperlyConfigured(
        "AZURE_COMMUNICATION_CONNECTION_STRING is required for the Azure mailer."
    )

_origin = urlsplit(PUBLIC_APP_ORIGIN)
_origin_host = (_origin.hostname or "").lower().rstrip(".")
try:
    _origin_is_local = not ip_address(_origin_host).is_global
except ValueError:
    _origin_is_local = "." not in _origin_host or _origin_host.endswith(
        (".localhost", ".local")
    )
if _origin.scheme != "https" or _origin_is_local:
    raise ImproperlyConfigured(
        "PUBLIC_APP_ORIGIN must use HTTPS with a nonlocal hostname in production."
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
