# AI contribution: 50% or more AI-generated
"""Django application configuration for audit."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.audit"
    verbose_name = "Audit"
