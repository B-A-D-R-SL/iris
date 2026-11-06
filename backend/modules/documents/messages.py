# AI contribution: 50% or more AI-generated
"""Translated messages for the notice rules in `domain/notice.py` (review rule 7).

`domain/` cannot use Django translations, so it reports a `Problem` per field
and this module gives each one its French or English text.
"""

from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from modules.documents.domain.notice import (
    EARLIEST_TAX_YEAR,
    MAX_REASON_LENGTH,
    NoticeRulesBroken,
    Problem,
)

_MESSAGES: dict[Problem, Promise] = {
    Problem.REQUIRED: _("Enter this information."),
    Problem.TAX_YEAR_TOO_EARLY: _("Enter a tax year from %(year)s on."),
    Problem.TAX_YEAR_NOT_ENDED: _("Enter a tax year that has ended."),
    Problem.NOTICE_DATE_TOO_EARLY: _(
        "The notice date must be after the end of the tax year."
    ),
    Problem.NOTICE_DATE_IN_FUTURE: _("The notice date cannot be in the future."),
    Problem.NEGATIVE_INCOME: _("Enter an amount of 0 or more."),
    Problem.REASON_REQUIRED: _("Explain why this person did not file a tax return."),
    Problem.REASON_TOO_LONG: _("Use at most %(count)s characters."),
    Problem.NOT_ALLOWED: _(
        "Leave this empty when the person did not file a tax return."
    ),
    Problem.FILE_EMPTY: _("The file is empty."),
    Problem.FILE_TOO_LARGE: _("The file is larger than the allowed size."),
    Problem.FILE_TYPE: _("Choose a JPEG, PNG or PDF file."),
}

_PARAMETERS = {"year": EARLIEST_TAX_YEAR, "count": MAX_REASON_LENGTH}


def problem_messages(error: NoticeRulesBroken) -> dict[str, list[str]]:
    """Each field's message in the active language, ready for a ValidationError."""
    return {
        field: [str(_MESSAGES[problem]) % _PARAMETERS]
        for field, problem in error.problems.items()
    }
