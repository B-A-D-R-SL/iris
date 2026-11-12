# AI contribution: 50% or more AI-generated
"""Reconcile the publication and household-status audit migration branches."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0004_alter_auditevent_action"),
        ("audit", "0004_auditevent_suspension_actions"),
    ]

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
                ],
                max_length=20,
            ),
        ),
    ]
