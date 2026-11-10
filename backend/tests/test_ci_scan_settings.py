# AI contribution: 50% or more AI-generated
"""The CI scan settings differ from production only where the runner needs it."""

import json
import os
import subprocess
import sys

KEYS = [
    "DEBUG",
    "SECURE_SSL_REDIRECT",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "ALLOWED_HOSTS",
    "MIDDLEWARE",
    "REST_FRAMEWORK",
    "AUTH_PASSWORD_VALIDATORS",
]


def _settings(module: str) -> dict[str, object]:
    """Load a settings module in a fresh process and read the compared values."""
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": module,
        "DJANGO_SECRET_KEY": "ci-scan-settings-test-key",
        "DJANGO_ALLOWED_HOSTS": "localhost",
    }
    code = (
        "import django, json; django.setup(); from django.conf import settings; "
        f"print(json.dumps({{k: getattr(settings, k) for k in {KEYS!r}}}, default=str))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_ci_scan_keeps_production_settings_except_the_https_redirect() -> None:
    """Only SECURE_SSL_REDIRECT changes; DEBUG stays off and cookies stay secure."""
    production = _settings("iris.settings.production")
    ci_scan = _settings("iris.settings.ci_scan")

    assert production["SECURE_SSL_REDIRECT"] is True
    assert ci_scan["SECURE_SSL_REDIRECT"] is False
    assert ci_scan["DEBUG"] is False
    assert {k: v for k, v in ci_scan.items() if k != "SECURE_SSL_REDIRECT"} == {
        k: v for k, v in production.items() if k != "SECURE_SSL_REDIRECT"
    }
