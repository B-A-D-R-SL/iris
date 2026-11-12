# AI contribution: 50% or more AI-generated
"""ASGI config for the Iris project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "iris.settings.production")

# Identify ASGI before Django loads settings and applies its connection policy.
os.environ["IRIS_SERVER_INTERFACE"] = "asgi"

application = get_asgi_application()
