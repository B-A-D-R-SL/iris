# AI contribution: 50% or more AI-generated
"""Operator recovery for approved partner applications whose email was lost."""

from argparse import ArgumentParser
from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
    ValidationError,
)
from django.core.management.base import BaseCommand, CommandError

from modules.stores import services
from modules.stores.models import PartnerApplication


class Command(BaseCommand):
    """Reissue the invitation without printing the recipient or bearer token."""

    help = "Reissue an approved partner application's invitation and email it after commit."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Use opaque application/admin identifiers, never contact details."""
        parser.add_argument("application_id", type=UUID)
        parser.add_argument("--admin-id", type=UUID, required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        """Require an active admin and leave application decisions unchanged."""
        user_model = get_user_model()
        try:
            admin = user_model.objects.get(pk=options["admin_id"])
            application = PartnerApplication.objects.get(pk=options["application_id"])
            services.resend_approval_invitation(application, admin)
        except (user_model.DoesNotExist, PartnerApplication.DoesNotExist) as exc:
            raise CommandError("Application or admin was not found.") from exc
        except (PermissionDenied, ValidationError, ImproperlyConfigured) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"Invitation reissued for application {application.pk}. "
            "Check email-failure events for delivery failures."
        )
