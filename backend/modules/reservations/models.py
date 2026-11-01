# AI contribution: 50% or more AI-generated
# I have drafted a plan, told AI to implement it, and reviewed the code
"""Reservations, following docs/03-design/database-schema.md.

Pickup workflows stay with the reservation stories. These columns exist so
the SET-18 seed can store fictional reservations.
"""

import uuid

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class ReservationStatus(models.TextChoices):
    """Reservation status. Labels live in the glossary."""

    RESERVED = "reserved", _("Reserved")
    PICKED_UP = "picked_up", _("Picked up")
    CANCELLED = "cancelled", _("Cancelled")
    CANCELLED_BY_STORE = "cancelled_by_store", _("Cancelled by store")
    NO_SHOW = "no_show", _("No-show")


class MadeByType(models.TextChoices):
    """Who created the reservation."""

    HOUSEHOLD = "household", _("Household")
    STAFF = "staff", _("Staff")


class Reservation(models.Model):
    """A household claim on a quantity of one listing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    quantity = models.IntegerField()
    pickup_code = models.CharField(max_length=6, validators=[MinLengthValidator(6)])
    status = models.CharField(max_length=32, choices=ReservationStatus.choices)
    late_cancel = models.BooleanField(default=False)
    made_by_type = models.CharField(max_length=16, choices=MadeByType.choices)
    made_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservations_made",
    )
    picked_up_at = models.DateTimeField(null=True, blank=True, default=None)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        default=None,
        on_delete=models.PROTECT,
        related_name="reservations_confirmed",
    )

    class Meta:
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.UniqueConstraint(
                fields=["listing", "pickup_code"],
                name="reservations_listing_pickup_code_uniq",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="reservations_quantity_at_least_one",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ReservationStatus.values),
                name="reservations_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(made_by_type__in=MadeByType.values),
                name="reservations_made_by_type_valid",
            ),
        ]

    def __str__(self) -> str:
        return self.pickup_code
