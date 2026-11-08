# AI contribution: 50% or more AI-generated
"""Read the shared household-size setting."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from modules.rules import queries as rule_queries


def max_household_people() -> int:
    """Require a published limit; the holder counts as one person."""
    rule = rule_queries.active("household_size")
    limit = None if rule is None else rule.values.get("max_people")
    if type(limit) is not int or limit < 1:
        raise ValidationError(_("Household size rules need configuration."))
    return limit
