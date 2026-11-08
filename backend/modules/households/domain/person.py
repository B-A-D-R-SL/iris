# AI contribution: 50% or more AI-generated
"""Pure person validation and duplicate-candidate key logic."""

from datetime import date

from .address import _fold

MAX_NAME_LENGTH = 100
MAX_PERSON_AGE = 120
ADULT_AGE = 18
MIN_HOLDER_AGE = ADULT_AGE


class BirthDateOutOfRange(ValueError):
    """Date of birth in the future or more than 120 years ago."""


class HolderTooYoung(ValueError):
    """The account holder is under 18."""


class InvalidPersonName(ValueError):
    """A first or last name with characters other than letters, spaces, ' or -."""


def valid_name(name: str) -> bool:
    value = name.strip()
    return (
        1 <= len(value) <= MAX_NAME_LENGTH
        and all(c.isalpha() or c in " -'’" for c in value)
        and any(c.isalpha() for c in value)
    )


def age_in_years(birth: date, today: date) -> int:
    return (
        today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    )


def is_adult(birth: date, today: date) -> bool:
    """18 or older on `today` (BR-DOC-007; eligibility counts the same adults)."""
    return age_in_years(birth, today) >= ADULT_AGE


def validate_birth_date(birth: date, today: date, *, holder: bool = False) -> None:
    if birth > today or age_in_years(birth, today) > MAX_PERSON_AGE:
        raise BirthDateOutOfRange("Enter a date of birth within the last 120 years.")
    if holder and age_in_years(birth, today) < MIN_HOLDER_AGE:
        raise HolderTooYoung("The account holder must be at least 18.")


def normalize_person(first_name: str, last_name: str, birth: date) -> str:
    if not valid_name(first_name) or not valid_name(last_name):
        raise InvalidPersonName("Enter a valid first and last name.")
    return "|".join((_fold(last_name), _fold(first_name), birth.isoformat()))
