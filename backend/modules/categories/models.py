# AI contribution: 50% or more AI-generated

"""Goods categories that every listing belongs to."""

import uuid

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """A kind of goods, for example bakery or personal hygiene.

    Rows come from data/categories.yaml (SET-12). A category in use is
    deactivated, never deleted (US-35).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=40, unique=True)
    name_fr = models.CharField(max_length=80)
    name_en = models.CharField(max_length=80)
    is_food = models.BooleanField()
    default_value_cents = models.BigIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.CheckConstraint(
                condition=Q(default_value_cents__gte=0),
                name="categories_default_value_cents_non_negative",
            )
        ]

    def __str__(self) -> str:
        return self.code
