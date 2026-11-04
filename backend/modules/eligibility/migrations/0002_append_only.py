# AI contribution: 50% or more AI-generated
"""Prevent database-level modification of eligibility decision history."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("eligibility", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION eligibility_reject_mutation()
                RETURNS trigger AS $$
                BEGIN
                    RAISE EXCEPTION 'Eligibility decisions are append-only.'
                        USING ERRCODE = '23000';
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER eligibility_append_only
                    BEFORE UPDATE OR DELETE
                    ON eligibility_eligibilitydecision
                    FOR EACH STATEMENT
                    EXECUTE FUNCTION eligibility_reject_mutation();
            """,
            reverse_sql="""
                DROP TRIGGER eligibility_append_only
                    ON eligibility_eligibilitydecision;
                DROP FUNCTION eligibility_reject_mutation();
            """,
        ),
    ]
