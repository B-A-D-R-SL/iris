# AI contribution: 50% or more AI-generated
"""ASGI config for the Iris project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iris.settings.local")

# Configure ASGI before get_asgi_application() loads the Django settings.
# Database settings stay in settings/base.py; WSGI keeps its normal lifetime.
os.environ["DATABASE_CONN_MAX_AGE"] = "0"

application = get_asgi_application()
