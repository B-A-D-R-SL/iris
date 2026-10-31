import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("households", "0001_initial"),
        ("listings", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Reservation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("quantity", models.IntegerField()),
                (
                    "pickup_code",
                    models.CharField(
                        max_length=6,
                        validators=[django.core.validators.MinLengthValidator(6)],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("reserved", "Reserved"),
                            ("picked_up", "Picked up"),
                            ("cancelled", "Cancelled"),
                            ("cancelled_by_store", "Cancelled by store"),
                            ("no_show", "No-show"),
                        ],
                        max_length=32,
                    ),
                ),
                ("late_cancel", models.BooleanField(default=False)),
                (
                    "made_by_type",
                    models.CharField(
                        choices=[("household", "Household"), ("staff", "Staff")],
                        max_length=16,
                    ),
                ),
                (
                    "picked_up_at",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
                (
                    "confirmed_by",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations_confirmed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations",
                        to="households.household",
                    ),
                ),
                (
                    "listing",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations",
                        to="listings.listing",
                    ),
                ),
                (
                    "made_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reservations_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Reservation",
                "verbose_name_plural": "Reservations",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("listing", "pickup_code"),
                        name="reservations_listing_pickup_code_uniq",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("quantity__gte", 1)),
                        name="reservations_quantity_at_least_one",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "status__in",
                                [
                                    "reserved",
                                    "picked_up",
                                    "cancelled",
                                    "cancelled_by_store",
                                    "no_show",
                                ],
                            )
                        ),
                        name="reservations_status_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("made_by_type__in", ["household", "staff"])
                        ),
                        name="reservations_made_by_type_valid",
                    ),
                ],
            },
        ),
    ]
