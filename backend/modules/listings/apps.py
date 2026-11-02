# AI contribution: 50% or more AI-generated

"""Django configuration for the listings module."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ListingsConfig(AppConfig):
    """Register the Listing model for goods posted by stores."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.listings"
    verbose_name = _("Listings")
