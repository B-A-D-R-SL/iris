# AI contribution: 50% or more AI-generated

"""Django configuration for the categories module."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CategoriesConfig(AppConfig):
    """Register the Category model that classifies every listing."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.categories"
    verbose_name = _("Categories")
