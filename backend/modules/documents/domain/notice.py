# AI contribution: 50% or more AI-generated
"""Notice of assessment rules BR-DOC-001 to BR-DOC-004, in plain Python (review rule 1).

The functions report every problem at once, by field name, so a form can show
each message under its field. `documents.messages` gives the translated text.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import NamedTuple, cast

# Oldest tax year Iris accepts; the rules schema uses the same lower bound.
EARLIEST_TAX_YEAR = 2000
MAX_REASON_LENGTH = 500

NOTICE_FIELDS: tuple[str, ...] = (
    "tax_year",
    "total_income_cents",
    "name_on_notice",
    "postal_code_on_notice",
    "notice_date",
    "seen_in_person",
)


class Problem(StrEnum):
    REQUIRED = "required"
    TAX_YEAR_TOO_EARLY = "tax_year_too_early"
    TAX_YEAR_NOT_ENDED = "tax_year_not_ended"
    NOTICE_DATE_TOO_EARLY = "notice_date_too_early"
    NOTICE_DATE_IN_FUTURE = "notice_date_in_future"
    NEGATIVE_INCOME = "negative_income"
    REASON_REQUIRED = "reason_required"
    REASON_TOO_LONG = "reason_too_long"
    NOT_ALLOWED = "not_allowed"
    FILE_EMPTY = "file_empty"
    FILE_TOO_LARGE = "file_too_large"
    FILE_TYPE = "file_type"


class NoticeRulesBroken(ValueError):
    """One or more fields break a notice rule; `problems` maps field to problem."""

    def __init__(self, problems: dict[str, Problem]) -> None:
        self.problems = problems
        super().__init__(", ".join(f"{field}: {p}" for field, p in problems.items()))


@dataclass(frozen=True)
class FiledNotice:
    tax_year: int
    total_income_cents: int
    name_on_notice: str
    postal_code_on_notice: str
    notice_date: date
    seen_in_person: bool


@dataclass(frozen=True)
class DidNotFile:
    reason: str


class FileType(NamedTuple):
    content_type: str
    extension: str


# BR-DOC-004: the type comes from the first bytes, never the name or declared type.
_SIGNATURES: tuple[tuple[bytes, FileType], ...] = (
    (b"%PDF-", FileType("application/pdf", "pdf")),
    (b"\xff\xd8\xff", FileType("image/jpeg", "jpg")),
    (b"\x89PNG\r\n\x1a\n", FileType("image/png", "png")),
)


def _missing(value: object) -> bool:
    return value is None or value == ""


def _raise_if(problems: dict[str, Problem]) -> None:
    if problems:
        raise NoticeRulesBroken(problems)


def parse_entry(
    values: Mapping[str, object], *, has_file: bool, today: date
) -> FiledNotice | DidNotFile:
    """Check a staff entry: a filed notice (BR-DOC-001/002) or a non-filer (BR-DOC-003)."""
    if values.get("did_not_file"):
        return _did_not_file(values, has_file=has_file)
    return _filed(values, has_file=has_file, today=today)


def _did_not_file(values: Mapping[str, object], *, has_file: bool) -> DidNotFile:
    problems: dict[str, Problem] = {}
    reason = values.get("did_not_file_reason")
    text = reason.strip() if isinstance(reason, str) else ""
    if not text:
        problems["did_not_file_reason"] = Problem.REASON_REQUIRED
    elif len(text) > MAX_REASON_LENGTH:
        problems["did_not_file_reason"] = Problem.REASON_TOO_LONG
    if has_file:
        problems["file"] = Problem.NOT_ALLOWED
    for field in NOTICE_FIELDS:
        value = values.get(field)
        # An unticked "seen in person" box is fine; only a notice can be seen.
        refused = value is True if field == "seen_in_person" else not _missing(value)
        if refused:
            problems[field] = Problem.NOT_ALLOWED
    _raise_if(problems)
    return DidNotFile(text)


def _filed(values: Mapping[str, object], *, has_file: bool, today: date) -> FiledNotice:
    problems = {
        field: Problem.REQUIRED
        for field in NOTICE_FIELDS
        if _missing(values.get(field))
    }
    if not has_file:
        problems["file"] = Problem.REQUIRED
    if not _missing(values.get("did_not_file_reason")):
        problems["did_not_file_reason"] = Problem.NOT_ALLOWED
    problems.update(_value_problems(values, today))
    _raise_if(problems)
    return FiledNotice(
        tax_year=cast(int, values["tax_year"]),
        total_income_cents=cast(int, values["total_income_cents"]),
        name_on_notice=cast(str, values["name_on_notice"]),
        postal_code_on_notice=cast(str, values["postal_code_on_notice"]),
        notice_date=cast(date, values["notice_date"]),
        seen_in_person=cast(bool, values["seen_in_person"]),
    )


def _value_problems(values: Mapping[str, object], today: date) -> dict[str, Problem]:
    """BR-DOC-001 income and BR-DOC-002 tax year and notice date, for given values."""
    problems: dict[str, Problem] = {}
    income = values.get("total_income_cents")
    if isinstance(income, int) and income < 0:
        problems["total_income_cents"] = Problem.NEGATIVE_INCOME
    tax_year = values.get("tax_year")
    valid_year: int | None = None
    if isinstance(tax_year, int):
        if tax_year < EARLIEST_TAX_YEAR:
            problems["tax_year"] = Problem.TAX_YEAR_TOO_EARLY
        elif tax_year >= today.year:
            problems["tax_year"] = Problem.TAX_YEAR_NOT_ENDED
        else:
            valid_year = tax_year
    notice_date = values.get("notice_date")
    if isinstance(notice_date, date):
        if notice_date > today:
            problems["notice_date"] = Problem.NOTICE_DATE_IN_FUTURE
        elif valid_year is not None and notice_date <= date(valid_year, 12, 31):
            problems["notice_date"] = Problem.NOTICE_DATE_TOO_EARLY
    return problems


def detect_file_type(content: bytes, max_bytes: int) -> FileType:
    """BR-DOC-004: a non-empty JPEG, PNG or PDF of at most `max_bytes`."""
    if not content:
        raise NoticeRulesBroken({"file": Problem.FILE_EMPTY})
    if len(content) > max_bytes:
        raise NoticeRulesBroken({"file": Problem.FILE_TOO_LARGE})
    for signature, file_type in _SIGNATURES:
        if content.startswith(signature):
            return file_type
    raise NoticeRulesBroken({"file": Problem.FILE_TYPE})
