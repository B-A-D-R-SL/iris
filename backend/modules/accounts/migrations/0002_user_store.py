# Generated for T-01.01.2.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("stores", "0003_validate_e164_phone"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="store",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="stores.store",
            ),
        ),
    ]
