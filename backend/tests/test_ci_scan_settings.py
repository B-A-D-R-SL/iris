# AI contribution: 50% or more AI-generated
"""The CI scan settings differ from production only where the runner needs it."""

import importlib
import sys
from collections.abc import Iterator
from types import ModuleType

import pytest

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
# Reloaded together so production sees this test's environment, not pytest's.
MODULES = ("iris.settings.ci_scan", "iris.settings.production", "iris.settings.base")
# Production (FIX-04) needs at least 50 characters and no development prefix.
SECRET_KEY = "fix17-ci-scan-settings-test-key-0123456789abcdefghijklmnop"


def _load(module: str) -> ModuleType:
    """Import a settings module fresh, as a plain module (Django keeps its own)."""
    sys.modules.pop(module, None)
    return importlib.import_module(module)


@pytest.fixture
def modules(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[ModuleType, ModuleType]]:
    """Production and CI scan settings, loaded with the values CI gives them."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", SECRET_KEY)
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "localhost")
    monkeypatch.setenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
    saved = {name: sys.modules.pop(name, None) for name in MODULES}
    production = _load("iris.settings.production")
    ci_scan = _load("iris.settings.ci_scan")
    yield production, ci_scan
    # Put back the modules pytest's Django setup loaded.
    for name, module in saved.items():
        sys.modules.pop(name, None)
        if module is not None:
            sys.modules[name] = module


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
