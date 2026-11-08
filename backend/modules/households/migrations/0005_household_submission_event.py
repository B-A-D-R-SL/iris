# AI contribution: 50% or more AI-generated
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("households", "0004_normalize_duplicate_keys")]

    operations = [
        migrations.AlterField(
            model_name="householddraftevent",
            name="action",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("updated", "Updated"),
                    ("submitted", "Submitted"),
                ],
                max_length=12,
            ),
        ),
    ]
