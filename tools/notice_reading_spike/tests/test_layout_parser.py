# AI contribution: 50% or more AI-generated
"""parse_layout on a recorded (or synthetic) Document Intelligence result."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from layout_parser import LayoutCell, LayoutDocument, LayoutLine, parse_layout
from reader import UNREAD, NoticeReading
from score import TruthRow, contains_document_number

FIXTURES = Path(__file__).parent / "fixtures"
SYNTHETIC = "synthetic-layout-notice-003.json"  # hand-built; recorded files are layout-notice-NNN


def load_fixture(name: str) -> LayoutDocument:
    return LayoutDocument.from_analyze_result(json.loads((FIXTURES / name).read_text("utf-8")))


def truth_row_for(fixture: Path, truth: dict[str, TruthRow]) -> TruthRow:
    """The truth row of `[synthetic-]layout-notice-NNN.json`; fails clearly when there is none."""
    stem = fixture.stem.partition("layout-")[2]
    rows = [row for name, row in truth.items() if Path(name).stem == stem]
    assert rows, f"{fixture.name}: no row for {stem!r} in mock-data/notices/truth.csv"
    return rows[0]


def line(text: str, confidence: float = 0.99) -> LayoutLine:
    return LayoutLine(text, ((0, len(text), confidence),))


def cell(row: int, column: int, text: str, header: bool = False) -> LayoutCell:
    return LayoutCell(row, column, text, 0.97, header)


@pytest.mark.parametrize(
    "fixture", sorted(FIXTURES.glob("*layout-notice-*.json")), ids=lambda path: path.name
)
def test_parse_layout_never_returns_a_wrong_value_for_any_fixture(fixture, truth):
    """Every field equals its truth or is unread: a misread value must never come back."""
    row = truth_row_for(fixture, truth)
    reading = parse_layout(load_fixture(fixture.name))
    for name, expected in row.expected.items():
        assert getattr(reading, name).value in (expected, None), name


@pytest.mark.parametrize("name", [SYNTHETIC, "layout-notice-003.json"])
def test_parse_layout_reads_every_field_of_a_clean_pdf(name, truth):
    row = truth_row_for(FIXTURES / name, truth)
    reading = parse_layout(load_fixture(name))
    for field, expected in row.expected.items():
        assert getattr(reading, field).value == expected, field


def test_parse_layout_reads_the_recorded_photo_except_its_misread_postal_code(truth):
    """On the photo of notice 031 the OCR read the postal code H8C 3Z0 as `H8C 320`."""
    doc = load_fixture("layout-notice-031.json")
    assert any(printed.text.endswith("H8C 320") for printed in doc.lines)
    reading = parse_layout(doc)
    row = truth_row_for(FIXTURES / "layout-notice-031.json", truth)
    for field, expected in row.expected.items():
        if field != "postal_code":
            assert getattr(reading, field).value == expected, field
    assert reading.postal_code == UNREAD


def test_truth_row_for_names_a_fixture_without_a_truth_row(truth):
    with pytest.raises(AssertionError, match="layout-notice-999.json: no row for 'notice-999'"):
        truth_row_for(FIXTURES / "layout-notice-999.json", truth)


def test_truth_row_for_finds_recorded_and_synthetic_names(truth):
    assert truth_row_for(Path("layout-notice-031.json"), truth).file == "photos/notice-031.png"
    assert truth_row_for(FIXTURES / SYNTHETIC, truth).file == "pdf/notice-003.pdf"


def test_parse_layout_reads_line_199_established_amount_on_changed_return():
    reading = parse_layout(load_fixture(SYNTHETIC))
    assert reading.total_income_cents.value == 7517091  # établi, not déclaré (7432655)


def test_parse_layout_confidence_is_lowest_word_confidence_of_the_value():
    reading = parse_layout(load_fixture(SYNTHETIC))
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


def test_parse_layout_uses_the_shared_unit_rule_for_other_markers():
    doc = LayoutDocument(
        lines=(
            line("Zoé Jessica Lapointe"),
            line("7768, avenue Bennett, APP.4B"),
            line("Montréal (Québec)  H1M 2B3"),
        ),
        tables=(),
    )
    reading = parse_layout(doc)
    assert reading.street_name.value == "avenue Bennett"
    assert reading.unit.value == "4B"


def test_parse_layout_keeps_a_last_part_without_a_unit_marker_in_the_street_name():
    doc = LayoutDocument(
        lines=(
            line("Théodore Bolduc"),
            line("1016, boulevard de Maisonneuve, Ouest"),
            line("Montréal (Québec)  H6R 4C3"),
        ),
        tables=(),
    )
    reading = parse_layout(doc)
    assert reading.street_name.value == "boulevard de Maisonneuve, Ouest"
    assert reading.unit.value == ""


@pytest.mark.parametrize(
    "postal_line", ["Montréal (Québec)  H6R4C3", "Montréal (Québec)  H6R 4C3 "]
)
def test_parse_layout_reads_a_postal_code_without_space_or_with_trailing_space(postal_line):
    doc = LayoutDocument(
        lines=(line("Théodore Bolduc"), line("1016, boulevard Rosemont"), line(postal_line)),
        tables=(),
    )
    reading = parse_layout(doc)
    assert reading.postal_code.value == "H6R 4C3"
    assert reading.street_number.value == "1016"
    assert reading.full_name.value == "Théodore Bolduc"


def test_parse_layout_reads_name_and_street_when_the_postal_code_is_misread():
    doc = LayoutDocument(
        lines=(
            line("Karine Arsenault"),
            line("8382, avenue Querbes"),
            line("Montréal (Québec) H2X 387"),  # OCR read the S of H2X 3S7 as 8
        ),
        tables=(),
    )
    reading = parse_layout(doc)
    assert reading.full_name.value == "Karine Arsenault"
    assert reading.street_number.value == "8382"
    assert reading.street_name.value == "avenue Querbes"
    assert reading.postal_code == UNREAD


def test_parse_layout_accepts_date_on_the_line_after_the_label():
    doc = LayoutDocument(lines=(line("Date de l'avis :"), line("1er avril 2026")), tables=())
    assert str(parse_layout(doc).notice_date.value) == "2026-04-01"


def test_parse_layout_uses_a_later_date_label_when_the_first_is_not_followed_by_a_date():
    doc = LayoutDocument(
        lines=(
            line("Date de l'avis :"),
            line("QFFF1GXI9D9"),  # a photo's reading order put the notice number here
            line("Date de l'avis"),  # the page footer prints the label without a colon
            line("30 avril 2026"),
        ),
        tables=(),
    )
    assert str(parse_layout(doc).notice_date.value) == "2026-04-30"


@pytest.mark.parametrize("assessed", ["61 700,73\nTIF", "IF\n61 700,73"])
def test_parse_layout_reads_income_from_a_cell_with_stray_watermark_text(assessed):
    table = (
        cell(0, 0, "Ligne", True),
        cell(0, 4, "Montant établi", True),
        cell(1, 0, "199"),
        cell(1, 4, assessed),
    )
    reading = parse_layout(LayoutDocument(lines=(), tables=(table,)))
    assert reading.total_income_cents.value == 6170073


def test_parse_layout_leaves_income_unread_when_a_cell_holds_two_amounts():
    table = (
        cell(0, 0, "Ligne", True),
        cell(0, 4, "Montant établi", True),
        cell(1, 0, "199"),
        cell(1, 4, "61 700,73\n1 234,00"),
    )
    reading = parse_layout(LayoutDocument(lines=(), tables=(table,)))
    assert reading.total_income_cents == UNREAD


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
    doc = load_fixture(SYNTHETIC)
    assert any("QI65FDHJK1E" in printed.text for printed in doc.lines)  # it is on the page
    assert not contains_document_number(parse_layout(doc))


def test_from_analyze_result_rejects_a_malformed_result():
    with pytest.raises(ValueError, match="unexpected AnalyzeResult shape"):
        LayoutDocument.from_analyze_result({"pages": [{"lines": [{"content": "no spans"}]}]})
