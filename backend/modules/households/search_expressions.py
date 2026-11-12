# AI contribution: 50% or more AI-generated
"""Shared SQL expressions so search predicates match their PostgreSQL indexes."""

from django.db.models import Func, TextField, Value
from django.db.models.functions import Concat


class SearchKey(Func):
    """Fold case and accents with the fixed dictionary installed by migration 0004."""

    function = "public.iris_household_search_key"
    output_field = TextField()


def member_name_key() -> SearchKey:
    # Deliberately excludes person_key: that duplicate key also contains DOB.
    return SearchKey(Concat("last_name", Value(" "), "first_name"))


def address_search_key() -> SearchKey:
    return SearchKey(
        Concat(
            "street_number",
            Value(" "),
            "street_name",
            Value(" "),
            "unit",
            Value(" "),
            "city",
            Value(" "),
            "postal_code",
        )
    )
