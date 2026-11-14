# AI contribution: 50% or more AI-generated
"""Canadian contact values and their canonical storage representation."""

import re
import unicodedata

_POSTAL = re.compile(
    r"[ABCEGHJ-NPRSTVXY][0-9][ABCEGHJ-NPRSTV-Z][0-9][ABCEGHJ-NPRSTV-Z][0-9]"
)
_PHONE = re.compile(r"\+1[2-9][0-9]{9}")
_POSTAL_PREFIX_LENGTH = 3


class InvalidPostalCode(ValueError):
    """Not a Canadian postal code in the A1A 1A1 format."""


class InvalidPhone(ValueError):
    """Not a ten-digit Canadian phone number."""


def normalize_postal_code(postal_code: str) -> str:
    """Return canonical Canadian format, preserving US-17's Unicode folding."""
    folded = unicodedata.normalize("NFKD", postal_code.strip().upper())
    without_accents = "".join(c for c in folded if not unicodedata.combining(c))
    compact = re.sub(r"\s+", "", without_accents)
    if not _POSTAL.fullmatch(compact):
        raise InvalidPostalCode("Enter a Canadian postal code like H2X 1Y4.")
    return f"{compact[:_POSTAL_PREFIX_LENGTH]} {compact[_POSTAL_PREFIX_LENGTH:]}"


def normalize_phone(phone: str) -> str:
    """Accept familiar separators and return +1 followed by ten ASCII digits."""
    compact = re.sub(r"[\s().-]", "", phone)
    if re.fullmatch(r"[0-9]{10}", compact):
        compact = "+1" + compact
    elif re.fullmatch(r"1[0-9]{10}", compact):
        compact = "+" + compact
    if not _PHONE.fullmatch(compact):
        raise InvalidPhone("Enter a 10-digit Canadian telephone number.")
    return compact
