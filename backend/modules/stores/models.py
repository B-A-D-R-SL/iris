# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code

"""Store records shared by B.A.D.R. and approved partner businesses."""

import re
import uuid

from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models
from django.db.models import Q

from modules.stores.fields import CitextEmailField

POSTAL_CODE_PATTERN = r"^[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d$"


class Store(models.Model):
    """A place that can offer goods for pickup in Iris."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, validators=[MinLengthValidator(2)])
    street_number = models.CharField(max_length=10)
    street_name = models.CharField(max_length=120)
    unit = models.CharField(max_length=10, null=True, blank=True, default=None)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(
        max_length=7,
        validators=[
            RegexValidator(POSTAL_CODE_PATTERN, "Enter a Canadian postal code.")
        ],
    )
    phone = models.CharField(max_length=16)
    email = CitextEmailField(max_length=254)
    opening_hours = models.JSONField(default=dict)
    pickup_instructions = models.CharField(
        max_length=300, null=True, blank=True, default=None
    )
    is_badr = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # The target schema's nullable application FK arrives with PartnerApplication.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
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
