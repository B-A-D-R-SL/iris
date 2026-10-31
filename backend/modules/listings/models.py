# AI contribution: 50% or more AI-generated

"""Goods posted by a store for households to reserve and pick up."""

import uuid

from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

MAX_QUANTITY = 999
MAX_PER_HOUSEHOLD = 10
MAX_ESTIMATED_VALUE_CENTS = 100_000


class ListingUnit(models.TextChoices):
    """How the quantity of a listing is counted."""

    ITEM = "item", _("Item")
    BUNDLE = "bundle", _("Bundle")


class ListingStatus(models.TextChoices):
    """Lifecycle of a listing; posting publishes it immediately."""

    PUBLISHED = "published", _("Published")
    CLOSED = "closed", _("Closed")
    CANCELLED = "cancelled", _("Cancelled")


class Listing(models.Model):
    """One offer of goods from a store, with stock and a pickup window.

    Reservations change quantity_reserved only through the listings service,
    with a single conditional UPDATE; the CHECK constraints below are the
    last line of defence against overbooking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    store = models.ForeignKey("stores.Store", on_delete=models.PROTECT)
    category = models.ForeignKey("categories.Category", on_delete=models.PROTECT)
    title = models.CharField(max_length=80, validators=[MinLengthValidator(2)])
    description = models.CharField(max_length=500, null=True, blank=True, default=None)
    quantity_total = models.IntegerField()
    quantity_reserved = models.IntegerField(default=0)
    unit = models.CharField(
        max_length=10, choices=ListingUnit.choices, default=ListingUnit.ITEM
    )
    max_per_household = models.SmallIntegerField(default=1)
    pickup_start = models.DateTimeField()
    pickup_end = models.DateTimeField()
    best_before = models.DateField(null=True, blank=True, default=None)
    photo_ref = models.CharField(max_length=300, null=True, blank=True, default=None)
    estimated_value_cents = models.BigIntegerField(null=True, blank=True, default=None)
    status = models.CharField(
        max_length=10, choices=ListingStatus.choices, default=ListingStatus.PUBLISHED
    )
    safe_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="safe_confirmed_listings",
    )
    safe_confirmed_at = models.DateTimeField()
    published_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True, default=None)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_listings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Listing")
        verbose_name_plural = _("Listings")
        constraints = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.CheckConstraint(
                condition=Q(quantity_total__gte=1, quantity_total__lte=MAX_QUANTITY),
                name="listings_quantity_total_range",
            ),
            models.CheckConstraint(
                condition=Q(
                    quantity_reserved__gte=0,
                    quantity_reserved__lte=F("quantity_total"),
                ),
                name="listings_quantity_reserved_within_total",
            ),
            models.CheckConstraint(
                condition=Q(
                    max_per_household__gte=1,
                    max_per_household__lte=MAX_PER_HOUSEHOLD,
                ),
                name="listings_max_per_household_range",
            ),
            models.CheckConstraint(
                condition=Q(pickup_end__gt=F("pickup_start")),
                name="listings_pickup_end_after_start",
            ),
            models.CheckConstraint(
                condition=Q(estimated_value_cents__isnull=True)
                | Q(
                    estimated_value_cents__gte=0,
                    estimated_value_cents__lte=MAX_ESTIMATED_VALUE_CENTS,
                ),
                name="listings_estimated_value_cents_range",
            ),
            models.CheckConstraint(
                condition=Q(unit__in=ListingUnit.values),
                name="listings_unit_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ListingStatus.values),
                name="listings_status_valid",
            ),
        ]
        indexes = [  # noqa: RUF012 - Django reads declarative model metadata.
            models.Index(
                fields=["status", "pickup_end"], name="listings_status_pickup_end_idx"
            ),
            models.Index(
                fields=["store", "pickup_start"], name="listings_store_pickup_idx"
            ),
        ]

    def __str__(self) -> str:
        return self.title
