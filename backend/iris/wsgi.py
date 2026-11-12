# AI contribution: 50% or more AI-generated
"""WSGI config for the Iris project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.checks import ERROR, Tags, run_checks
from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import WSGIHandler
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iris.settings.production")


def _checked_application() -> WSGIHandler:
    """Load and validate routes before a server accepts its first request."""
    application = get_wsgi_application()
    # Route imports belong to startup, as with runserver's checks. This does not
    # execute household searches or warm database query results.
    errors = [
        check.id or "unidentified URL error"
        for check in run_checks(tags=[Tags.urls])
        if check.level >= ERROR
    ]
    if errors:
        raise ImproperlyConfigured(f"Invalid URL configuration: {', '.join(errors)}")
    return application


application = _checked_application()
