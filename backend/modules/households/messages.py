# AI contribution: 50% or more AI-generated
"""Translated messages for the errors raised by the plain-Python domain rules.

`domain/` cannot use Django translations, so it raises specific error types and
this module gives each one its French or English message for API responses.
"""

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from modules.households.domain.address import IncompleteAddress, InvalidPostalCode
from modules.households.domain.person import (
    BirthDateOutOfRange,
    HolderTooYoung,
    InvalidPersonName,
)

_MESSAGES: dict[type[ValueError], Promise] = {
    BirthDateOutOfRange: _(
        "Enter a date of birth within the last 120 years, not in the future."
    ),
    HolderTooYoung: _("The account holder must be 18 or older."),
    InvalidPersonName: _("Use letters, spaces, apostrophes or hyphens."),
    InvalidPostalCode: _("Enter a Canadian postal code, for example H2X 1Y4."),
    IncompleteAddress: _("Enter the street number and street name."),
}

_FALLBACK = _("Check this value.")


def domain_error_message(error: ValueError) -> Promise:
    """The user-facing message for a domain error, in the request's language."""
    for error_type, message in _MESSAGES.items():
        if isinstance(error, error_type):
            return message
    return _FALLBACK
