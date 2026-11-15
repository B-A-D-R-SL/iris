# AI contribution: 50% or more AI-generated
"""Add the store update and deactivation audit actions (US-14)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audit", "0005_merge_publication_and_suspension_actions")]

    operations = [
        migrations.AlterField(
            model_name="auditevent",
            name="action",
            field=models.CharField(
                choices=[
                    ("view", "View"),
                    ("decision", "Decision"),
                    ("rule_published", "Rule Published"),
                    ("suspend", "Suspend"),
                    ("reactivate", "Reactivate"),
                    ("update", "Update"),
                    ("deactivate", "Deactivate"),
                ],
                max_length=20,
            ),
        ),
    ]
