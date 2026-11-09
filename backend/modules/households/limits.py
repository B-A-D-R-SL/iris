# AI contribution: 50% or more AI-generated
"""Read the shared household-size setting."""

import logging

from modules.households.exceptions import HouseholdUnavailable
from modules.rules import queries as rule_queries

logger = logging.getLogger("iris.households")


def max_household_people() -> int:
    """Require a published limit; the holder counts as one person."""
    rule = rule_queries.active("household_size")
    values = {} if rule is None or not isinstance(rule.values, dict) else rule.values
    limit = values.get("max_people")
    if type(limit) is not int or limit < 1:
        logger.error(
            "Household size rules unavailable",
            extra={"event": "household_size_unavailable"},
        )
        raise HouseholdUnavailable
    return limit
