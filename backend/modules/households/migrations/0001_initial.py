# Generated schema migration for T-03.17.2 / T-03.17.3.
# REVIEW with `python manage.py makemigrations --check --dry-run`.
import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Household",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        serialize=False,
                        editable=False,
                    ),
                ),
                (
                    "member_number",
                    models.CharField(max_length=10, unique=True, null=True, blank=True),
                ),
                (
                    "channel",
                    models.CharField(
                        max_length=12,
                        choices=[("online", "Online"), ("walk_in", "Walk-in")],
                        default="walk_in",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("draft", "Draft"),
                            ("submitted", "Submitted"),
                            ("review_required", "Review required"),
                            ("awaiting_visit", "Awaiting visit"),
                            ("approved", "Approved"),
                            ("renewal_needed", "Renewal needed"),
                            ("suspended", "Suspended"),
                            ("rejected", "Rejected"),
                        ],
                        default="draft",
                    ),
                ),
                ("email", models.EmailField(max_length=254, null=True, blank=True)),
                (
                    "preferred_language",
                    models.CharField(
                        max_length=2,
                        choices=[("fr", "Français"), ("en", "English")],
                        default="fr",
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        max_length=16,
                        validators=[
                            django.core.validators.RegexValidator(
                                r"^\+1\d{10}$", "Enter a Canadian telephone number."
                            )
                        ],
                    ),
                ),
                ("street_number", models.CharField(max_length=10, blank=True)),
                ("street_name", models.CharField(max_length=120, blank=True)),
                ("unit", models.CharField(max_length=10, blank=True)),
                ("city", models.CharField(max_length=80, blank=True)),
                ("postal_code", models.CharField(max_length=7, blank=True)),
                (
                    "address_key",
                    models.CharField(max_length=200, blank=True, db_index=True),
                ),
                ("alternate_name", models.CharField(max_length=100, blank=True)),
                ("alternate_phone", models.CharField(max_length=16, blank=True)),
                (
                    "alternate_email",
                    models.EmailField(max_length=254, null=True, blank=True),
                ),
                ("identity_checked_in_person", models.BooleanField(default=False)),
                ("submitted_at", models.DateTimeField(null=True, blank=True)),
                ("approved_at", models.DateTimeField(null=True, blank=True)),
                ("expires_at", models.DateTimeField(null=True, blank=True)),
                ("status_reason", models.CharField(max_length=500, blank=True)),
                ("verified_at", models.DateTimeField(null=True, blank=True)),
                ("anonymized_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "holder",
                    models.OneToOneField(
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="household",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="households_created",
                    ),
                ),
                (
                    "verified_by",
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="households_verified",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["status", "expires_at"],
                        name="households__status_4f9d18_idx",
                    )
                ]
            },
        ),
        migrations.CreateModel(
            name="Member",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True,
                        default=uuid.uuid4,
                        serialize=False,
                        editable=False,
                    ),
                ),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(max_length=100)),
                ("date_of_birth", models.DateField()),
                (
                    "relation",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("holder", "Holder"),
                            ("spouse_partner", "Spouse or partner"),
                            ("child", "Child"),
                            ("parent", "Parent"),
                            ("sibling", "Sibling"),
                            ("grandparent", "Grandparent"),
                            ("grandchild", "Grandchild"),
                            ("other_relative", "Other relative"),
                            ("other", "Other"),
                        ],
                    ),
                ),
                (
                    "person_key",
                    models.CharField(
                        max_length=220, db_index=True, blank=True, editable=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "household",
                    models.ForeignKey(
                        to="households.household",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="member",
            constraint=models.UniqueConstraint(
                fields=["household"],
                condition=models.Q(relation="holder"),
                name="households_one_holder_member",
            ),
        ),
        migrations.CreateModel(
            name="HouseholdDraftEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "action",
                    models.CharField(
                        max_length=12,
                        choices=[("created", "Created"), ("updated", "Updated")],
                    ),
                ),
                ("actor_role", models.CharField(max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        on_delete=django.db.models.deletion.PROTECT,
                    ),
                ),
                (
                    "household",
                    models.ForeignKey(
                        to="households.household",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="draft_events",
                    ),
                ),
            ],
        ),
    ]
