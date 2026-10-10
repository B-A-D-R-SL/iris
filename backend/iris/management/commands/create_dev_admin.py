# AI contribution: 50% or more AI-generated
"""Idempotently create the local-only Iris administrator."""

import os
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update the development administrator (local settings only)."

    def handle(self, *args: Any, **options: Any) -> str:
        if not settings.DEBUG:
            raise CommandError("create_dev_admin is available only when DEBUG=True")

        email = os.environ.get("DJANGO_DEV_ADMIN_EMAIL", "admin@iris.local").strip()
        password = os.environ.get("DJANGO_DEV_ADMIN_PASSWORD", "")
        if not email or not password:
            raise CommandError("DJANGO_DEV_ADMIN_EMAIL and DJANGO_DEV_ADMIN_PASSWORD are required")

        user_model = get_user_model()
        user, created = user_model._default_manager.get_or_create(username=email)

        if hasattr(user, "email"):
            user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "created" if created else "updated"
        message = f"Development administrator {action}: {email}"
        self.stdout.write(self.style.SUCCESS(message))
        return message
