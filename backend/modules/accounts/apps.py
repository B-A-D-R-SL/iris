# AI contribution: 50% or more AI-generated
"""Django application configuration for accounts."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.accounts"
    verbose_name = "Accounts"

    def ready(self) -> None:
        """Register account signal handlers."""
        from modules.accounts import signals  # noqa: F401
