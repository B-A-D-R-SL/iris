# AI contribution: 50% or more AI-generated
"""Index audit search: one household's history, and date ranges (FIX-19).

Both indexes read newest first, like the search. Reversing drops them; no data
changes.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("audit", "0008_auditevent_store_actions")]

    operations = [
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(
                fields=["target_type", "target_id", "-created_at", "-id"],
                name="audit_target_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["-created_at", "-id"], name="audit_created_idx"),
        ),
    ]
