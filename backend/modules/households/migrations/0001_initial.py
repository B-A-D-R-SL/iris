import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Household",
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
                (
                    "channel",
                    models.CharField(
                        choices=[("walk-in", "Walk-in"), ("online", "Online")],
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("review_required", "Staff review required"),
                            ("awaiting_visit", "In-person visit required"),
                            ("approved", "Approved"),
                            ("renewal_needed", "Renewal required"),
                            ("suspended", "Suspended"),
                            ("rejected", "Rejected"),
                        ],
                        max_length=32,
                    ),
                ),
                ("street_number", models.CharField(max_length=10)),
                ("street_name", models.CharField(max_length=120)),
                (
                    "unit",
                    models.CharField(
                        blank=True, default=None, max_length=10, null=True
                    ),
                ),
                ("city", models.CharField(max_length=80)),
                (
                    "postal_code",
                    models.CharField(
                        max_length=7,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[A-Za-z]\\d[A-Za-z] ?\\d[A-Za-z]\\d$",
                                "Enter a Canadian postal code.",
                            )
                        ],
                    ),
                ),
                ("address_key", models.CharField(max_length=300)),
                (
                    "phone",
                    models.CharField(
                        max_length=16,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^\\+[1-9]\\d{1,14}$",
                                "Enter a phone number in E.164 format.",
                            )
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "verified_at",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
                (
                    "approved_at",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
                (
                    "expires_at",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_households",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "verified_by",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="verified_households",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Household",
                "verbose_name_plural": "Households",
                "indexes": [
                    models.Index(
                        fields=["address_key"], name="households_address_key_idx"
                    ),
                    models.Index(fields=["status"], name="households_status_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("channel__in", ["walk-in", "online"])),
                        name="households_channel_valid",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "status__in",
                                [
                                    "draft",
                                    "submitted",
                                    "review_required",
                                    "awaiting_visit",
                                    "approved",
                                    "renewal_needed",
                                    "suspended",
                                    "rejected",
                                ],
                            )
                        ),
                        name="households_status_valid",
                    ),
                ],
            },
        ),
    ]
