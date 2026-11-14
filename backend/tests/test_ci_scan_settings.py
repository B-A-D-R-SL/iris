# AI contribution: 50% or more AI-generated
"""The CI scan settings differ from production only where the runner needs it."""

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured

KEYS = [
    "DEBUG",
    "SECURE_SSL_REDIRECT",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "ALLOWED_HOSTS",
    "MIDDLEWARE",
    "REST_FRAMEWORK",
    "AUTH_PASSWORD_VALIDATORS",
    "MAILER_ADAPTER",
    "DEFAULT_FROM_EMAIL",
    "PUBLIC_APP_ORIGIN",
]
# Reloaded together so production sees this test's environment, not pytest's.
MODULES = ("iris.settings.ci_scan", "iris.settings.production", "iris.settings.base")
# Production (FIX-04) needs at least 50 characters and no development prefix.
SECRET_KEY = "fix17-ci-scan-settings-test-key-0123456789abcdefghijklmnop"


def _load(module: str) -> ModuleType:
    """Import a settings module fresh, as a plain module (Django keeps its own)."""
    sys.modules.pop(module, None)
    return importlib.import_module(module)


def _set_ci_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use the synthetic mail configuration supplied by the workflow."""
    for key, value in {
        "DJANGO_SECRET_KEY": SECRET_KEY,
        "DJANGO_ALLOWED_HOSTS": "localhost",
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "MAILER_ADAPTER": "smtp",
        "DEFAULT_FROM_EMAIL": "noreply@iris.example.org",
        "PUBLIC_APP_ORIGIN": "https://iris.example.org",
    }.items():
        monkeypatch.setenv(key, value)


@contextmanager
def _isolated_modules() -> Iterator[None]:
    """Restore pytest's modules even when a startup guard rejects an import."""
    saved = {name: sys.modules.pop(name, None) for name in MODULES}
    try:
        yield
    finally:
        for name, module in saved.items():
            sys.modules.pop(name, None)
            if module is not None:
                sys.modules[name] = module


@pytest.fixture
def modules(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[ModuleType, ModuleType]]:
    """Production and CI scan settings, loaded with the values CI gives them."""
    _set_ci_environment(monkeypatch)
    with _isolated_modules():
        yield _load("iris.settings.production"), _load("iris.settings.ci_scan")


def test_ci_scan_keeps_production_settings_except_the_https_redirect(
    modules: tuple[ModuleType, ModuleType],
) -> None:
    """Only SECURE_SSL_REDIRECT changes; DEBUG stays off and cookies stay secure."""
    production, ci_scan = modules

    assert production.SECURE_SSL_REDIRECT is True
    assert ci_scan.SECURE_SSL_REDIRECT is False
    assert ci_scan.DEBUG is False
    for key in KEYS:
        if key != "SECURE_SSL_REDIRECT":
            assert getattr(ci_scan, key) == getattr(production, key), key


def test_ci_scan_adds_the_seed_command_package(
    modules: tuple[ModuleType, ModuleType],
) -> None:
    """The seed command lives in the iris package, which production does not load."""
    production, ci_scan = modules

    assert "iris" not in production.INSTALLED_APPS
    assert ci_scan.INSTALLED_APPS == [*production.INSTALLED_APPS, "iris"]


def test_ci_scan_keeps_the_production_startup_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A weak key still stops the scan backend: ci_scan inherits FIX-04's checks."""
    _set_ci_environment(monkeypatch)
    monkeypatch.setenv("DJANGO_SECRET_KEY", "too-short-for-production")
    with (
        _isolated_modules(),
        pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"),
    ):
        _load("iris.settings.ci_scan")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("MAILER_ADAPTER", "fake"),
        ("DEFAULT_FROM_EMAIL", "noreply@iris.local"),
        ("DEFAULT_FROM_EMAIL", "not-an-address"),
        ("PUBLIC_APP_ORIGIN", "http://iris.example.org"),
        ("PUBLIC_APP_ORIGIN", "https://localhost"),
    ],
)
def test_ci_scan_preserves_email_startup_guards(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str
) -> None:
    """The scan inherits US-57 validation instead of bypassing delivery settings."""
    _set_ci_environment(monkeypatch)
    monkeypatch.setenv(key, value)
    with _isolated_modules(), pytest.raises(ImproperlyConfigured, match=key):
        _load("iris.settings.ci_scan")
