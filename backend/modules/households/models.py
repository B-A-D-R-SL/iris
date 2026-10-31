# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""Household files, following docs/03-design/database-schema.md.

Registration workflows stay with the household stories. These columns exist
so the SET-18 seed can store fictional files.
"""

import re
import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

POSTAL_CODE_PATTERN = r"^[A-Za-z]\d[A-Za-z] ?\d[A-Za-z]\d$"
E164_PHONE_NUMBER_PATTERN = r"^\+[1-9]\d{1,14}$"


class HouseholdChannel(models.TextChoices):
    """How the household file was opened."""

    WALK_IN = "walk-in", _("Walk-in")
    ONLINE = "online", _("Online")


class HouseholdStatus(models.TextChoices):
    """File status. Labels live in the glossary."""

    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    REVIEW_REQUIRED = "review_required", _("Staff review required")
    AWAITING_VISIT = "awaiting_visit", _("In-person visit required")
    APPROVED = "approved", _("Approved")
    RENEWAL_NEEDED = "renewal_needed", _("Renewal required")
    SUSPENDED = "suspended", _("Suspended")
    REJECTED = "rejected", _("Rejected")


class Household(models.Model):
    """A household registration file. Members are added by later stories."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.CharField(max_length=16, choices=HouseholdChannel.choices)
    status = models.CharField(max_length=32, choices=HouseholdStatus.choices)
    street_number = models.CharField(max_length=10)
    street_name = models.CharField(max_length=120)
    unit = models.CharField(max_length=10, null=True, blank=True, default=None)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(
        max_length=7,
        validators=[
            RegexValidator(POSTAL_CODE_PATTERN, _("Enter a Canadian postal code."))
        ],
    )
    address_key = models.CharField(max_length=300)
    phone = models.CharField(
        max_length=16,
        validators=[
            RegexValidator(
                E164_PHONE_NUMBER_PATTERN,
                _("Enter a phone number in E.164 format."),
            )
        ],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_households",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT,
        related_name="verified_households",
    )
    verified_at = models.DateTimeField(null=True, blank=True, default=None)
    approved_at = models.DateTimeField(null=True, blank=True, default=None)
    expires_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        verbose_name = _("Household")
        verbose_name_plural = _("Households")
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.CheckConstraint(
                condition=Q(channel__in=HouseholdChannel.values),
                name="households_channel_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=HouseholdStatus.values),
                name="households_status_valid",
            ),
        ]
        indexes = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.Index(fields=["address_key"], name="households_address_key_idx"),
            models.Index(fields=["status"], name="households_status_idx"),
        ]

    def clean(self) -> None:
        """Store a valid Canadian postal code in uppercase with one space."""
        super().clean()
        compact_code = self.postal_code.replace(" ", "").upper()
        if re.fullmatch(r"[A-Z]\d[A-Z]\d[A-Z]\d", compact_code):
            self.postal_code = f"{compact_code[:3]} {compact_code[3:]}"

    def __str__(self) -> str:
        return self.phone
