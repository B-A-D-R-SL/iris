# AI contribution: 50% or more AI-generated
"""Add the store deactivation audit action (US-14).

Store edits use the ``update`` action that 0006 already added for households.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audit", "0007_enforce_system_actor")]

    operations = [
        migrations.AlterField(
            model_name="auditevent",
            name="action",
            field=models.CharField(
                choices=[
                    ("view", "View"),
                    ("create", "Create"),
                    ("update", "Update"),
                    ("submit", "Submit"),
                    ("decision", "Decision"),
                    ("rule_published", "Rule Published"),
                    ("suspend", "Suspend"),
                    ("reactivate", "Reactivate"),
                    ("deactivate", "Deactivate"),
                ],
                max_length=20,
            ),
        ),
    ]
