# AI contribution: 50% or more AI-generated
"""FIX-04: production startup refuses unsafe settings before serving requests."""

import json
import os
import subprocess
import sys

import pytest

TEST_SECRET_KEY = "fix04-production-test-key-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def _run(
    arguments: list[str], **overrides: str | None
) -> subprocess.CompletedProcess[str]:
    """Load settings in a fresh interpreter, outside pytest's cached Django setup."""
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "iris.settings.production",
        "DJANGO_SECRET_KEY": TEST_SECRET_KEY,
        "DJANGO_ALLOWED_HOSTS": "staging.example.test",
        "EMAIL_BACKEND": SMTP_BACKEND,
    }
    environment.pop("IRIS_SERVER_INTERFACE", None)
    for name, value in overrides.items():
        if value is None:
            environment.pop(name, None)
        else:
            environment[name] = value
    return subprocess.run(
        [sys.executable, *arguments],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize(
    "secret_key",
    [
        "CHANGE_ME_LOCAL_ONLY",
        "iris-insecure-local-dev-key-change-before-deploying",
        "django-insecure-" + TEST_SECRET_KEY,
        "iris-insecure-" + TEST_SECRET_KEY,
        TEST_SECRET_KEY[:49],
        "",
    ],
)
def test_production_refuses_short_or_development_secret_keys(secret_key: str) -> None:
    # rule: SEC-01 — published development secrets must never boot production.
    result = _run(
        ["-c", "import iris.settings.production"], DJANGO_SECRET_KEY=secret_key
    )

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "DJANGO_SECRET_KEY must contain at least 50 characters" in result.stderr


def test_production_accepts_the_50_character_secret_key_boundary() -> None:
    result = _run(
        ["-c", "import iris.settings.production; print('configured')"],
        DJANGO_SECRET_KEY=TEST_SECRET_KEY[:50],
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "configured"


@pytest.mark.parametrize("backend", ["console", "locmem"])
def test_production_refuses_console_and_in_memory_mailers(backend: str) -> None:
    result = _run(
        ["-c", "import iris.settings.production"],
        EMAIL_BACKEND=f"django.core.mail.backends.{backend}.EmailBackend",
    )

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "EMAIL_BACKEND must deliver email in production" in result.stderr


def test_production_requires_allowed_hosts() -> None:
    result = _run(["-c", "import iris.settings.production"], DJANGO_ALLOWED_HOSTS="")

    assert result.returncode != 0
    assert "DJANGO_ALLOWED_HOSTS must be configured in production" in result.stderr


@pytest.mark.parametrize("database_url", ["", "sqlite:///:memory:"])
def test_production_keeps_the_required_postgresql_database(database_url: str) -> None:
    result = _run(["-c", "import iris.settings.production"], DATABASE_URL=database_url)

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "PostgreSQL" in result.stderr


def test_production_passes_the_strict_deployment_check() -> None:
    result = _run(["manage.py", "check", "--deploy", "--fail-level", "WARNING"])

    assert result.returncode == 0, result.stdout + result.stderr
    assert "System check identified no issues" in result.stdout + result.stderr


@pytest.mark.parametrize("entrypoint", ["wsgi", "asgi"])
def test_server_entrypoints_default_to_production(entrypoint: str) -> None:
    result = _run(
        [
            "-c",
            (
                f"import iris.{entrypoint}; from django.conf import settings; "
                "print(settings.SETTINGS_MODULE, settings.DEBUG)"
            ),
        ],
        DJANGO_SETTINGS_MODULE=None,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "iris.settings.production False"


@pytest.mark.parametrize("entrypoint", ["wsgi", "asgi"])
@pytest.mark.parametrize(
    "settings_module", ["iris.settings.local", "iris.settings.test"]
)
def test_entrypoints_keep_explicit_local_and_test_overrides(
    entrypoint: str, settings_module: str
) -> None:
    result = _run(
        [
            "-c",
            (
                f"import iris.{entrypoint}; from django.conf import settings; "
                "print(settings.SETTINGS_MODULE)"
            ),
        ],
        DJANGO_SETTINGS_MODULE=settings_module,
        DJANGO_SECRET_KEY="local-test-key",
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == settings_module


def test_manage_py_keeps_its_local_default() -> None:
    result = _run(
        [
            "manage.py",
            "shell",
            "-c",
            "from django.conf import settings; print(settings.DEBUG)",
        ],
        DJANGO_SETTINGS_MODULE=None,
        DJANGO_SECRET_KEY="local-test-key",
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("True")


def test_production_http_redirect_and_forwarded_https_hsts() -> None:
    result = _run(
        [
            "-c",
            (
                "import django, json; django.setup(); "
                "from django.test import Client; "
                "client = Client(HTTP_HOST='staging.example.test'); "
                "plain = client.get('/api/health/'); "
                "secure = client.get('/api/health/', HTTP_X_FORWARDED_PROTO='https'); "
                "print(json.dumps({'plain': plain.status_code, "
                "'location': plain['Location'], 'secure': secure.status_code, "
                "'body': secure.json(), 'hsts': secure['Strict-Transport-Security']}))"
            ),
        ]
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "plain": 301,
        "location": "https://staging.example.test/api/health/",
        "secure": 200,
        "body": {"status": "ok"},
        "hsts": "max-age=31536000; includeSubDomains",
    }


def test_production_security_policy_and_base_settings_are_independent() -> None:
    result = _run(
        [
            "-c",
            (
                "import iris.settings.production as production, iris.settings.base as base; "
                "import json; print(json.dumps({"
                "'secure_cookies': [production.SESSION_COOKIE_SECURE, production.CSRF_COOKIE_SECURE], "
                "'preload': production.SECURE_HSTS_PRELOAD, "
                "'silenced': production.SILENCED_SYSTEM_CHECKS, "
                "'proxy': production.SECURE_PROXY_SSL_HEADER, "
                "'base_throttles': base.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES'), "
                "'base_docs': base.SPECTACULAR_SETTINGS.get('SERVE_PERMISSIONS'), "
                "'rates': production.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']}))"
            ),
        ],
        DRF_ANON_THROTTLE_RATE="25/min",
        DRF_USER_THROTTLE_RATE="125/min",
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "secure_cookies": [True, True],
        "preload": False,
        "silenced": ["security.W021"],
        "proxy": ["HTTP_X_FORWARDED_PROTO", "https"],
        "base_throttles": None,
        "base_docs": None,
        "rates": {
            "partner_applications": "5/hour",
            "anon": "25/min",
            "user": "125/min",
        },
    }


@pytest.mark.parametrize("name", ["DRF_ANON_THROTTLE_RATE", "DRF_USER_THROTTLE_RATE"])
@pytest.mark.parametrize("rate", ["0/min", "-1/min", "five/min", "5/week", "5/", ""])
def test_production_refuses_disabled_or_malformed_throttle_rates(
    name: str, rate: str
) -> None:
    result = _run(["-c", "import iris.settings.production"], **{name: rate})

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert f"{name} must be a positive request count" in result.stderr


@pytest.mark.parametrize("proxy_count", ["-1", "-2"])
def test_production_refuses_negative_trusted_proxy_counts(proxy_count: str) -> None:
    result = _run(
        ["-c", "import iris.settings.production"], DRF_NUM_PROXIES=proxy_count
    )

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert "DRF_NUM_PROXIES must be zero or positive" in result.stderr
