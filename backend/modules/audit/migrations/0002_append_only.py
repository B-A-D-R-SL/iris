# AI contribution: 50% or more AI-generated
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION audit_reject_mutation() RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'Audit events are append-only.'
                        USING ERRCODE = '23000';
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER audit_append_only
                    BEFORE UPDATE OR DELETE ON audit_auditevent
                    FOR EACH STATEMENT EXECUTE FUNCTION audit_reject_mutation();
            """,
            reverse_sql="""
                DROP TRIGGER audit_append_only ON audit_auditevent;
                DROP FUNCTION audit_reject_mutation();
            """,
        ),
    ]
