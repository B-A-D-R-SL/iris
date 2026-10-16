from django.apps import AppConfig


class RulesConfig(AppConfig):
    """Configuration for the rule settings module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.rules"
    verbose_name = "Rule settings"
