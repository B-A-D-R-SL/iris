# AI contribution: 50% or more AI-generated
"""Pure address normalization used to discover *possible* duplicate households."""

import re
import unicodedata

from modules.common.domain.contact import normalize_postal_code

_STREET_TYPES = {"RUE": "R", "AVENUE": "AV", "BOULEVARD": "BD", "CHEMIN": "CH"}


class IncompleteAddress(ValueError):
    """Street number or street name missing."""


def _fold(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.strip().upper())
    without_accents = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents).strip()


def normalize_address(
    street_number: str, street_name: str, unit: str | None, postal_code: str
) -> str:
    """Build a stable address key; do not equate different apartments."""
    number = _fold(street_number)
    street = _fold(street_name)
    apartment = _fold(unit or "")
    if not number or not street:
        raise IncompleteAddress("Street number and street name are required.")
    # Only replace whole street-type tokens; e.g. 'RUE' not 'RUEIL'.
    street = " ".join(_STREET_TYPES.get(word, word) for word in street.split())
    postal = normalize_postal_code(postal_code).replace(" ", "")
    return f"{number}|{street}|{apartment}|{postal}"
