# AI contribution: 50% or more AI-generated
"""Parsers for French-Canadian notice text, shared by the Azure and Gemini readers."""

from __future__ import annotations

import datetime as dt
import re
import unicodedata

_AMOUNT = re.compile(r"\d+(,\d{1,2})?")
_DATE = re.compile(r"(\d{1,2})(?:er)?\s+([a-z]+)\s+(\d{4})")
_POSTAL = re.compile(r"([A-Z]\d[A-Z])\s?(\d[A-Z]\d)")
# "app. 106", "apt. 4B", "unité 12" or "# 7"; \b keeps words like "appartement" whole
_UNIT_MARKER = re.compile(r"(?:(?:app|apt|unit[eé])(?:\.|\b)|#)\s*", re.IGNORECASE)
_SPACES = re.compile(r"[\s  ]+")
_MONTHS = {
    name: number
    for number, name in enumerate(
        [
            "janvier",
            "fevrier",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "aout",
            "septembre",
            "octobre",
            "novembre",
            "decembre",
        ],
        start=1,
    )
}


def strip_accents(text: str) -> str:
    """Remove diacritics: OCR often drops them, and the name check ignores them."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def parse_amount_cents(text: str) -> int | None:
    """Parse "23 456,78" or "23 456,78 $" into cents; None when it is not an amount."""
    compact = _SPACES.sub("", text.replace("$", ""))
    if not _AMOUNT.fullmatch(compact):
        return None
    whole, _, fraction = compact.partition(",")
    return int(whole) * 100 + int(fraction.ljust(2, "0") or "0")


def parse_french_date(text: str) -> dt.date | None:
    """Parse "28 mars 2026" or "1er avril 2026"; a missing accent in the month is accepted."""
    match = _DATE.fullmatch(_SPACES.sub(" ", strip_accents(text).strip().casefold()))
    if match is None:
        return None
    day, month_name, year = match.groups()
    month = _MONTHS.get(month_name)
    if month is None:
        return None
    try:
        return dt.date(int(year), month, int(day))
    except ValueError:
        return None


def normalize_postal_code(text: str) -> str | None:
    """Return "H2X 4N1" from "h2x4n1" or "H2X 4N1"; None when it is not a postal code."""
    match = _POSTAL.fullmatch(text.strip().upper())
    return f"{match.group(1)} {match.group(2)}" if match else None


def normalize_unit(text: str) -> str:
    """Return "106" from "app. 106" (as printed), "apt. 106", "unité 106" or "# 106"; "" stays "".

    Both readers use it, so a unit scores the same whichever service read it.
    """
    stripped = text.strip()
    marker = _UNIT_MARKER.match(stripped)
    return stripped[marker.end() :].strip() if marker else stripped
