# AI contribution: 50% or more AI-generated
"""Django application configuration for households."""

from django.apps import AppConfig


class HouseholdsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.households"
    verbose_name = "Households"

    def ready(self) -> None:
        """Link invited accounts (US-93); files follow the holder's language (US-08)."""
        from modules.accounts import services as account_services
        from modules.households import account_link_services

        account_services.invitation_accepted.connect(
            account_link_services.link_invited_account,
            dispatch_uid="households.link_invited_account",
        )
        account_services.language_changed.connect(
            account_link_services.follow_holder_language,
            dispatch_uid="households.follow_holder_language",
        )
