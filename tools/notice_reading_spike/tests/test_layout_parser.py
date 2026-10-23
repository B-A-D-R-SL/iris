# AI contribution: 50% or more AI-generated
"""parse_layout on a recorded (or synthetic) Document Intelligence result."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from layout_parser import LayoutCell, LayoutDocument, LayoutLine, parse_layout
from reader import NoticeReading
from score import contains_document_number

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> LayoutDocument:
    return LayoutDocument.from_analyze_result(json.loads((FIXTURES / name).read_text("utf-8")))


def line(text: str, confidence: float = 0.99) -> LayoutLine:
    return LayoutLine(text, ((0, len(text), confidence),))


def cell(row: int, column: int, text: str, header: bool = False) -> LayoutCell:
    return LayoutCell(row, column, text, 0.97, header)


@pytest.mark.parametrize("fixture", sorted(FIXTURES.glob("layout-notice-*.json")))
def test_parse_layout_matches_truth_for_every_fixture(fixture, truth):
    stem = fixture.stem.removeprefix("layout-")
    row = next(row for name, row in truth.items() if Path(name).stem == stem)
    reading = parse_layout(load_fixture(fixture.name))
    for name, expected in row.expected.items():
        assert getattr(reading, name).value == expected, name


def test_parse_layout_reads_line_199_established_amount_on_changed_return():
    reading = parse_layout(load_fixture("layout-notice-003.json"))
    assert reading.total_income_cents.value == 7517091  # établi, not déclaré (7432655)


def test_parse_layout_confidence_is_lowest_word_confidence_of_the_value():
    reading = parse_layout(load_fixture("layout-notice-003.json"))
    assert reading.street_name.confidence == 0.87  # "Maisonneuve" is the weakest word
    assert reading.street_number.confidence > 0.9
    assert reading.total_income_cents.confidence >= 0.95


def test_parse_layout_splits_unit_from_app_suffix():
    doc = LayoutDocument(
        lines=(
            line("Zoé Jessica Lapointe"),
            line("7768, avenue Bennett, app. 106"),
            line("Montréal (Québec)  H1M 2B3"),
        ),
        tables=(),
    )
    reading = parse_layout(doc)
    assert reading.street_number.value == "7768"
    assert reading.street_name.value == "avenue Bennett"
    assert reading.unit.value == "106"
    assert reading.postal_code.value == "H1M 2B3"


def test_parse_layout_accepts_date_on_the_line_after_the_label():
    doc = LayoutDocument(lines=(line("Date de l'avis :"), line("1er avril 2026")), tables=())
    assert str(parse_layout(doc).notice_date.value) == "2026-04-01"


def test_parse_layout_matches_assessed_header_ignoring_case_and_accents():
    table = (
        cell(0, 0, "Ligne", True),
        cell(0, 3, "MONTANT ETABLI", True),
        cell(1, 0, "199"),
        cell(1, 3, "12 345,67"),
    )
    reading = parse_layout(LayoutDocument(lines=(), tables=(table,)))
    assert reading.total_income_cents.value == 1234567


def test_parse_layout_leaves_income_unread_without_an_assessed_column():
    table = (cell(0, 0, "Ligne", True), cell(0, 3, "Montant déclaré", True), cell(1, 0, "199"))
    reading = parse_layout(LayoutDocument(lines=(), tables=(table,)))
    assert reading.total_income_cents.value is None


def test_parse_layout_empty_document_returns_all_unread_fields():
    reading = parse_layout(LayoutDocument(lines=(), tables=()))
    for field in dataclasses.fields(NoticeReading):
        assert getattr(reading, field.name).value is None
        assert getattr(reading, field.name).confidence == 0.0


def test_parse_layout_never_returns_identification_or_notice_number():
    doc = load_fixture("layout-notice-003.json")
    assert any("QI65FDHJK1E" in printed.text for printed in doc.lines)  # it is on the page
    assert not contains_document_number(parse_layout(doc))


def test_from_analyze_result_rejects_a_malformed_result():
    with pytest.raises(ValueError, match="unexpected AnalyzeResult shape"):
        LayoutDocument.from_analyze_result({"pages": [{"lines": [{"content": "no spans"}]}]})
