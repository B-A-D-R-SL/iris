# AI contribution: 50% or more AI-generated
"""Pure notice rules BR-DOC-001 to BR-DOC-004 (T-03.18.2, tests for #467)."""

from datetime import date
from typing import Any

import pytest
from django.utils import translation

from modules.documents.domain.notice import (
    NOTICE_FIELDS,
    DidNotFile,
    FiledNotice,
    FileType,
    NoticeRulesBroken,
    Problem,
    detect_file_type,
    parse_entry,
)
from modules.documents.messages import problem_messages

TODAY = date(2026, 11, 6)
PDF = b"%PDF-1.7 notice"


def _filed(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "did_not_file": False,
        "tax_year": 2025,
        "total_income_cents": 1_234_500,
        "name_on_notice": "Example Holder",
        "postal_code_on_notice": "H2X 1Y4",
        "notice_date": date(2026, 4, 30),
        "seen_in_person": False,
    }
    return values | changes


def _problems(values: dict[str, Any], *, has_file: bool = True) -> dict[str, Problem]:
    with pytest.raises(NoticeRulesBroken) as caught:
        parse_entry(values, has_file=has_file, today=TODAY)
    return caught.value.problems


def test_br_doc_001_complete_filed_notice_is_accepted() -> None:
    assert parse_entry(_filed(), has_file=True, today=TODAY) == FiledNotice(
        tax_year=2025,
        total_income_cents=1_234_500,
        name_on_notice="Example Holder",
        postal_code_on_notice="H2X 1Y4",
        notice_date=date(2026, 4, 30),
        seen_in_person=False,
    )


@pytest.mark.parametrize("empty", [None, ""])
@pytest.mark.parametrize("field", NOTICE_FIELDS)
def test_br_doc_001_each_missing_value_is_reported(field: str, empty: Any) -> None:
    assert _problems(_filed(**{field: empty})) == {field: Problem.REQUIRED}


def test_br_doc_001_all_missing_values_are_reported_together() -> None:
    problems = _problems({}, has_file=False)

    assert problems == {
        "file": Problem.REQUIRED,
        "tax_year": Problem.REQUIRED,
        "total_income_cents": Problem.REQUIRED,
        "name_on_notice": Problem.REQUIRED,
        "postal_code_on_notice": Problem.REQUIRED,
        "notice_date": Problem.REQUIRED,
        "seen_in_person": Problem.REQUIRED,
    }


def test_br_doc_001_zero_income_is_accepted() -> None:
    entry = parse_entry(_filed(total_income_cents=0), has_file=True, today=TODAY)

    assert isinstance(entry, FiledNotice)
    assert entry.total_income_cents == 0


def test_br_doc_001_negative_income_is_refused() -> None:
    problems = _problems(_filed(total_income_cents=-1))

    assert problems == {"total_income_cents": Problem.NEGATIVE_INCOME}


def test_br_doc_001_reason_on_a_filed_notice_is_refused() -> None:
    problems = _problems(_filed(did_not_file_reason="No income"))

    assert problems == {"did_not_file_reason": Problem.NOT_ALLOWED}


def test_br_doc_002_notice_dated_january_first_after_the_tax_year_is_accepted() -> None:
    values = _filed(tax_year=2025, notice_date=date(2026, 1, 1))

    assert isinstance(parse_entry(values, has_file=True, today=TODAY), FiledNotice)


def test_br_doc_002_notice_dated_december_31_of_the_tax_year_is_refused() -> None:
    problems = _problems(_filed(tax_year=2025, notice_date=date(2025, 12, 31)))

    assert problems == {"notice_date": Problem.NOTICE_DATE_TOO_EARLY}


def test_br_doc_002_notice_dated_today_is_accepted() -> None:
    values = _filed(notice_date=TODAY)

    assert isinstance(parse_entry(values, has_file=True, today=TODAY), FiledNotice)


def test_br_doc_002_notice_dated_tomorrow_is_refused() -> None:
    problems = _problems(_filed(notice_date=date(2026, 11, 7)))

    assert problems == {"notice_date": Problem.NOTICE_DATE_IN_FUTURE}


def test_br_doc_002_tax_year_1999_is_refused() -> None:
    problems = _problems(_filed(tax_year=1999, notice_date=date(2000, 5, 1)))

    assert problems == {"tax_year": Problem.TAX_YEAR_TOO_EARLY}


@pytest.mark.parametrize("tax_year", [0, -1])
def test_br_doc_002_impossible_early_tax_year_is_refused_without_crashing(
    tax_year: int,
) -> None:
    problems = _problems(_filed(tax_year=tax_year))

    assert problems == {"tax_year": Problem.TAX_YEAR_TOO_EARLY}


def test_br_doc_002_tax_year_2000_is_accepted() -> None:
    values = _filed(tax_year=2000, notice_date=date(2001, 5, 1))

    assert isinstance(parse_entry(values, has_file=True, today=TODAY), FiledNotice)


def test_br_doc_002_current_tax_year_is_refused() -> None:
    problems = _problems(_filed(tax_year=2026, notice_date=date(2026, 11, 1)))

    assert problems == {"tax_year": Problem.TAX_YEAR_NOT_ENDED}


def test_br_doc_002_impossible_tax_year_is_refused_without_crashing() -> None:
    problems = _problems(_filed(tax_year=99_999))

    assert problems == {"tax_year": Problem.TAX_YEAR_NOT_ENDED}


def test_br_doc_003_did_not_file_with_reason_is_accepted() -> None:
    values = {"did_not_file": True, "did_not_file_reason": "  Pas de revenu  "}

    assert parse_entry(values, has_file=False, today=TODAY) == DidNotFile(
        "Pas de revenu"
    )


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_br_doc_003_reason_blank_or_spaces_is_required(reason: Any) -> None:
    problems = _problems(
        {"did_not_file": True, "did_not_file_reason": reason}, has_file=False
    )

    assert problems == {"did_not_file_reason": Problem.REASON_REQUIRED}


def test_br_doc_003_reason_of_500_characters_is_accepted() -> None:
    values = {"did_not_file": True, "did_not_file_reason": "a" * 500}

    assert parse_entry(values, has_file=False, today=TODAY) == DidNotFile("a" * 500)


def test_br_doc_003_reason_of_501_characters_is_refused() -> None:
    problems = _problems(
        {"did_not_file": True, "did_not_file_reason": "a" * 501}, has_file=False
    )

    assert problems == {"did_not_file_reason": Problem.REASON_TOO_LONG}


def test_br_doc_003_did_not_file_refuses_a_file_and_values() -> None:
    values = {"did_not_file": True, "did_not_file_reason": "None", "tax_year": 2025}

    assert _problems(values, has_file=True) == {
        "file": Problem.NOT_ALLOWED,
        "tax_year": Problem.NOT_ALLOWED,
    }


def test_br_doc_003_did_not_file_ignores_empty_values() -> None:
    values = {field: "" for field in NOTICE_FIELDS} | {
        "did_not_file": True,
        "did_not_file_reason": "No income in 2025",
        "seen_in_person": None,
    }

    assert parse_entry(values, has_file=False, today=TODAY) == DidNotFile(
        "No income in 2025"
    )


def test_br_doc_003_unticked_seen_in_person_is_accepted_on_did_not_file() -> None:
    values = {
        "did_not_file": True,
        "did_not_file_reason": "None",
        "seen_in_person": False,
    }

    assert parse_entry(values, has_file=False, today=TODAY) == DidNotFile("None")


def test_br_doc_003_seen_in_person_without_a_notice_is_refused() -> None:
    values = {
        "did_not_file": True,
        "did_not_file_reason": "None",
        "seen_in_person": True,
    }

    assert _problems(values, has_file=False) == {"seen_in_person": Problem.NOT_ALLOWED}


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"%PDF-1.7 notice", FileType("application/pdf", "pdf")),
        (b"\xff\xd8\xff\xe0 photo", FileType("image/jpeg", "jpg")),
        (b"\x89PNG\r\n\x1a\n scan", FileType("image/png", "png")),
    ],
)
def test_br_doc_004_detects_pdf_jpeg_and_png(
    content: bytes, expected: FileType
) -> None:
    assert detect_file_type(content, max_bytes=1_000) == expected


def _file_problems(content: bytes, max_bytes: int = 1_000) -> dict[str, Problem]:
    with pytest.raises(NoticeRulesBroken) as caught:
        detect_file_type(content, max_bytes=max_bytes)
    return caught.value.problems


def test_br_doc_004_html_named_as_pdf_is_refused() -> None:
    assert _file_problems(b"<html><script>alert(1)</script>") == {
        "file": Problem.FILE_TYPE
    }


def test_br_doc_004_empty_file_is_refused() -> None:
    assert _file_problems(b"") == {"file": Problem.FILE_EMPTY}


def test_br_doc_004_file_of_max_bytes_is_accepted() -> None:
    content = PDF + b"x" * (16 - len(PDF))

    assert detect_file_type(content, max_bytes=16) == FileType("application/pdf", "pdf")


def test_br_doc_004_file_one_byte_over_is_refused() -> None:
    content = PDF + b"x" * (17 - len(PDF))

    assert _file_problems(content, max_bytes=16) == {"file": Problem.FILE_TOO_LARGE}


@pytest.mark.parametrize("problem", list(Problem))
def test_every_problem_has_a_french_and_english_message(problem: Problem) -> None:
    error = NoticeRulesBroken({"field": problem})

    with translation.override("en"):
        english = problem_messages(error)["field"]
    with translation.override("fr"):
        french = problem_messages(error)["field"]

    assert english and french
    assert english != french
