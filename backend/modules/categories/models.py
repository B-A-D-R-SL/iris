# AI contribution: 50% or more AI-generated
"""Category definitions used to classify donated goods."""

import uuid

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """A category of goods that participating stores may donate."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=64,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-z][a-z0-9_]*$",
                message="Use lowercase letters, numbers and underscores.",
            )
        ],
    )

    name_fr = models.CharField(max_length=150)
    name_en = models.CharField(max_length=150)

    is_food = models.BooleanField(default=False)

    default_value_cents = models.PositiveBigIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("code",)
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self) -> str:
        return self.name_en
