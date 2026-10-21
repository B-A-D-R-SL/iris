# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Django configuration for the stores module."""

from django.apps import AppConfig


class StoresConfig(AppConfig):
    """Register the Store model and its Django admin configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.stores"
    verbose_name = "Stores"
