# AI contribution: 50% or more AI-generated
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_user_store")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE accounts_auth_cache (
                    cache_key varchar(255) PRIMARY KEY,
                    value text NOT NULL,
                    expires timestamp with time zone NOT NULL
                );
                CREATE INDEX accounts_auth_cache_expires
                    ON accounts_auth_cache (expires);
            """,
            reverse_sql="DROP TABLE accounts_auth_cache;",
        )
    ]
