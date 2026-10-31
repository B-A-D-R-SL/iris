# AI contribution: 50% or more AI-generated
"""Pure address normalization used to discover *possible* duplicate households."""

import re
import unicodedata

_POSTAL = re.compile(r"^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\d[ABCEGHJ-NPRSTV-Z]\d$")
_STREET_TYPES = {"RUE": "R", "AVENUE": "AV", "BOULEVARD": "BD", "CHEMIN": "CH"}


def _fold(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.strip().upper())
    without_accents = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_accents).strip()


def normalize_postal_code(postal_code: str) -> str:
    """Return canonical Canadian format, e.g. H2X 1Y4, or raise ValueError."""
    compact = re.sub(r"\s+", "", _fold(postal_code))
    if not _POSTAL.fullmatch(compact):
        raise ValueError("Enter a Canadian postal code like H2X 1Y4.")
    return f"{compact[:3]} {compact[3:]}"


def normalize_address(
    street_number: str, street_name: str, unit: str | None, postal_code: str
) -> str:
    """Build a stable address key; do not equate different apartments."""
    number = _fold(street_number)
    street = _fold(street_name)
    apartment = _fold(unit or "")
    if not number or not street:
        raise ValueError("Street number and street name are required.")
    # Only replace whole street-type tokens; e.g. 'RUE' not 'RUEIL'.
    street = " ".join(_STREET_TYPES.get(word, word) for word in street.split())
    postal = normalize_postal_code(postal_code).replace(" ", "")
    return f"{number}|{street}|{apartment}|{postal}"
