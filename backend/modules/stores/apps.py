# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Django configuration for the stores module."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StoresConfig(AppConfig):
    """Register the Store model and its Django admin configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.stores"
    verbose_name = _("Stores")
