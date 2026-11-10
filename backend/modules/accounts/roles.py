# AI contribution: 50% or more AI-generated
"""Role choices shared by the user model and public account queries."""

from django.db import models


class UserRole(models.TextChoices):
    BENEFICIARY = "beneficiary"
    STORE_STAFF = "store_staff"
    STORE_MANAGER = "store_manager"
    INTAKE_WORKER = "intake_worker"
    ADMIN = "admin"
