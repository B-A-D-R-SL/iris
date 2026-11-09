# AI contribution: 50% or more AI-generated
"""US-41: reservation timestamps and the two indexes from the database design.

Rows that already exist (the SET-18 seed) get the migration time as their
``created_at``. Reversing drops the columns and the indexes again.
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("households", "0001_initial"),
        ("listings", "0001_initial"),
        ("reservations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reservation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddIndex(
            model_name="reservation",
            index=models.Index(
                fields=["household", "status"],
                name="reservations_household_status",
            ),
        ),
        migrations.AddIndex(
            model_name="reservation",
            index=models.Index(
                fields=["status", "listing"],
                name="reservations_status_listing",
            ),
        ),
    ]
