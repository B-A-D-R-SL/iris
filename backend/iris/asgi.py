# AI contribution: 50% or more AI-generated
"""ASGI config for the Iris project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iris.settings.local")

# Async requests do not reuse WSGI worker threads. Django requires connection
# persistence to be disabled for ASGI; a backend pool can be configured separately.
settings.DATABASES["default"]["CONN_MAX_AGE"] = 0

application = get_asgi_application()
