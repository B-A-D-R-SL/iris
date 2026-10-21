# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Store records shared by B.A.D.R. and approved partner businesses."""

import re
import uuid

from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from modules.stores.fields import CitextEmailField

POSTAL_CODE_PATTERN = r"^[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d$"


class Store(models.Model):
    """A place that can offer goods for pickup in Iris."""

    id = models.UUIDField(
        pgettext_lazy("store field", "ID"),
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(
        pgettext_lazy("store field", "Store name"),
        max_length=150,
        validators=[MinLengthValidator(2)],
    )
    street_number = models.CharField(
        pgettext_lazy("store field", "Street number"), max_length=10
    )
    street_name = models.CharField(
        pgettext_lazy("store field", "Street"), max_length=120
    )
    unit = models.CharField(
        pgettext_lazy("store field", "Apt."),
        max_length=10,
        null=True,
        blank=True,
        default=None,
    )
    city = models.CharField(pgettext_lazy("store field", "City"), max_length=80)
    postal_code = models.CharField(
        pgettext_lazy("store field", "Postal code"),
        max_length=7,
        validators=[
            RegexValidator(POSTAL_CODE_PATTERN, _("Enter a Canadian postal code."))
        ],
    )
    phone = models.CharField(
        pgettext_lazy("store field", "Phone number"), max_length=16
    )
    email = CitextEmailField(
        pgettext_lazy("store field", "Email address"), max_length=254
    )
    opening_hours = models.JSONField(
        pgettext_lazy("store field", "Opening hours"), default=dict
    )
    pickup_instructions = models.CharField(
        pgettext_lazy("store field", "Pickup instructions"),
        max_length=300,
        null=True,
        blank=True,
        default=None,
    )
    is_badr = models.BooleanField(
        pgettext_lazy("store field", "B.A.D.R. store"), default=False
    )
    is_active = models.BooleanField(
        pgettext_lazy("store field", "Active"), default=True
    )
    # The target schema's nullable application FK arrives with PartnerApplication.
    created_at = models.DateTimeField(
        pgettext_lazy("store field", "Created at"), auto_now_add=True
    )
    updated_at = models.DateTimeField(
        pgettext_lazy("store field", "Updated at"), auto_now=True
    )

    class Meta:
        verbose_name = _("Store")
        verbose_name_plural = _("Stores")
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.UniqueConstraint(
                fields=["is_badr"],
                condition=Q(is_badr=True),
                name="stores_single_badr_store",
            )
        ]

    def clean(self) -> None:
        """Store valid Canadian postal codes in uppercase with one space."""
        super().clean()
        compact_code = self.postal_code.replace(" ", "").upper()
        if re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", compact_code):
            self.postal_code = f"{compact_code[:3]} {compact_code[3:]}"

    def __str__(self) -> str:
        return self.name
