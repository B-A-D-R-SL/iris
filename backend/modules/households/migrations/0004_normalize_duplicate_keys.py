# AI contribution: 50% or more AI-generated
"""Update old address and person keys for duplicate checks."""

import re
import unicodedata

from django.db import migrations

# Keep this copy so later rule changes do not affect old migrations.
POSTAL = re.compile(r"^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\d[ABCEGHJ-NPRSTV-Z]\d$")
STREET_TYPES = {"RUE": "R", "AVENUE": "AV", "BOULEVARD": "BD", "CHEMIN": "CH"}


def fold(value):
    decomposed = unicodedata.normalize("NFKD", value.strip().upper())
    return re.sub(
        r"\s+", " ", "".join(c for c in decomposed if not unicodedata.combining(c))
    ).strip()


def normalize_keys(apps, schema_editor):
    alias = schema_editor.connection.alias
    households = apps.get_model("households", "Household").objects.using(alias)
    members = apps.get_model("households", "Member").objects.using(alias)
    for household in households.iterator():
        postal = re.sub(r"\s+", "", fold(household.postal_code))
        key = ""
        if (
            household.anonymized_at is None
            and household.street_number.strip()
            and household.street_name.strip()
            and household.city.strip()
            and POSTAL.fullmatch(postal)
        ):
            street = " ".join(
                STREET_TYPES.get(word, word)
                for word in fold(household.street_name).split()
            )
            key = "|".join(
                (
                    fold(household.street_number),
                    street,
                    fold(household.unit or ""),
                    postal,
                )
            )
        households.filter(pk=household.pk).update(address_key=key)
    for member in members.select_related("household").iterator():
        key = ""
        if (
            member.household.anonymized_at is None
            and member.first_name.strip()
            and member.last_name.strip()
        ):
            key = "|".join(
                (
                    fold(member.last_name),
                    fold(member.first_name),
                    member.date_of_birth.isoformat(),
                )
            )
        members.filter(pk=member.pk).update(person_key=key)


class Migration(migrations.Migration):
    dependencies = [("households", "0003_household_consent")]

    operations = [
        # Old versions also accept these keys, so keep them on rollback.
        migrations.RunPython(normalize_keys, reverse_code=migrations.RunPython.noop),
    ]
