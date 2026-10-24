# AI contribution: 50% or more AI-generated
"""Checks the scorer against hand-built truth rows and the real mock truth file."""

from __future__ import annotations

import dataclasses
import datetime as dt

from conftest import make_reading, make_row

from reader import NoticeReading, ReadField
from records import RunRecord
from score import (
    ADDRESS_FIELDS,
    CONFIDENT,
    DEV_FILES,
    contains_document_number,
    score_reading,
    summarize,
)

SETTINGS = {"commit": "abc1234", "reader": "test", "date": "2026-10-23"}


def test_load_truth_reads_all_50_files(truth):
    assert len(truth) == 50
    row = truth["pdf/notice-001.pdf"]
    assert (row.last_name, row.total_income_cents, row.notice_date) == (
        "Lefebvre",
        3165104,
        dt.date(2026, 3, 21),
    )
    assert row.unit == ""
    assert truth["photos/notice-050.png"].case == "unreadable"


def test_dev_files_are_eight_existing_truth_files(truth):
    assert len(DEV_FILES) == 8
    assert DEV_FILES <= set(truth)


def test_score_reading_none_marks_every_field_missing():
    score = score_reading(make_row(), None)
    assert set(score.outcomes.values()) == {"missing"}
    assert score.confident_wrong_fields == ()


def test_score_reading_all_correct():
    row = make_row()
    score = score_reading(row, make_reading(row))
    assert set(score.outcomes.values()) == {"correct"}


def test_score_name_ignores_case_and_accents_like_the_name_check():
    row = make_row()
    score = score_reading(row, make_reading(row, full_name="ZOE  JESSICA LAPOINTE"))
    assert score.outcomes["full_name"] == "correct"
    wrong = score_reading(row, make_reading(row, full_name="Zoé Lapointe"))
    assert wrong.outcomes["full_name"] == "wrong"


def test_score_street_name_is_normalized_but_postal_code_is_exact():
    row = make_row()
    reading = make_reading(row, street_name="BOULEVARD SAINT-LAURENT", postal_code="h2x 4n1")
    outcomes = score_reading(row, reading).outcomes
    assert outcomes["street_name"] == "correct"
    assert outcomes["postal_code"] == "wrong"


def test_score_income_must_be_exact_cents():
    row = make_row(total_income_cents=7517090)
    score = score_reading(row, make_reading(row, total_income_cents=7517091))
    assert score.outcomes["total_income_cents"] == "wrong"


def test_score_unit_empty_string_matches_no_unit_and_none_is_missing():
    row = make_row(unit="")
    assert score_reading(row, make_reading(row)).outcomes["unit"] == "correct"
    assert score_reading(row, make_reading(row, unit=None)).outcomes["unit"] == "missing"


def test_address_correct_only_when_all_four_address_fields_are():
    row = make_row()
    assert score_reading(row, make_reading(row)).all_correct(ADDRESS_FIELDS) is True
    wrong_number = make_reading(row, street_number="1925")
    assert score_reading(row, wrong_number).all_correct(ADDRESS_FIELDS) is False


def test_confident_wrong_counts_only_wrong_fields_at_or_above_threshold():
    row = make_row()
    reading = NoticeReading(
        full_name=ReadField("Someone Else", CONFIDENT),  # wrong, confident
        street_number=ReadField("1925", CONFIDENT - 0.01),  # wrong, not confident
        street_name=ReadField(row.street_name, 1.0),  # correct
        unit=ReadField(None, 1.0),  # missing is not a confident wrong value
        postal_code=ReadField("H0H 0H0", 0.99),  # wrong, confident
        tax_year=ReadField(2025, 1.0),
        total_income_cents=ReadField(1, 0.2),  # wrong, not confident
        notice_date=ReadField(row.notice_date, 1.0),
    )
    score = score_reading(row, reading)
    assert score.confident_wrong_fields == ("full_name", "postal_code")


def test_contains_document_number_flags_notice_and_control_numbers():
    row = make_row()
    assert contains_document_number(make_reading(row, street_number="Q1234567890"))
    assert contains_document_number(make_reading(row, street_number="12345678901"))
    assert contains_document_number(make_reading(row, full_name="Zoé M1234567890"))
    assert not contains_document_number(make_reading(row, street_number="1924"))
    assert not contains_document_number(make_reading(row, street_name="rue Maisonneuve"))
    assert not contains_document_number(make_reading(row))


def _records(truth, mutate=None) -> list[RunRecord]:
    records = []
    for name, row in truth.items():
        reading = mutate(name, row) if mutate else make_reading(row)
        error = None if reading else "DocumentReadError"
        records.append(RunRecord(name, reading, 2.0, error, 0.01))
    return records


def _table_row(summary: str, label: str) -> str:
    return next(line for line in summary.splitlines() if line.startswith(f"| {label} |"))


def test_summary_reports_changed_returns_and_unreadable_rows_separately(truth):
    def mutate(name, row):
        if name == "pdf/notice-003.pdf":  # a changed return read as the declared amount
            return make_reading(row, total_income_cents=row.total_income_cents - 100)
        if name == "photos/notice-050.png":  # unreadable photo, two fields at high confidence
            reading = make_reading(row, confidence=0.2)
            return dataclasses.replace(
                reading, tax_year=ReadField(2025, 0.95), street_number=ReadField("1", 0.91)
            )
        if name == "pdf/notice-046.pdf":
            return None
        return make_reading(row)

    summary = summarize(_records(truth, mutate), truth, SETTINGS)
    assert "Changed returns, income accuracy (7 files): 85.7%" in summary
    assert "notice-050 outcome: 2 field(s) at confidence >= 0.90" in summary
    assert "Failures: 1" in summary
    assert "document_number_leaks: 0" in summary
    assert "Median seconds: 2.0" in summary
    assert "p95 seconds: 2.0" in summary
    assert "Mean cost per notice (USD): 0.0100" in summary
    # Held-out PDFs: 29 (006-030, 046-049), 046 failed. Held-out photos: 034-045, the
    # unreadable 050 is excluded. Dev: 001-005 and 031-033, 003 read the declared amount.
    assert _table_row(summary, "total income") == (
        "| total income | 96.6% (28/29) | 100.0% (12/12) | 87.5% (7/8) | 1 |"
    )


def test_summary_columns_measure_held_out_pdfs_and_photos_apart_from_dev(truth):
    summary = summarize(_records(truth), truth, SETTINGS)
    assert (
        "| Field | Held-out PDFs | Held-out photos | Dev (all) | Confident-and-wrong |"
        in summary.splitlines()
    )


def test_summary_starts_with_the_settings_block_in_order(truth):
    settings = {"commit": "abc1234", "reader": "vlm", "model": "m", "date": "2026-10-23"}
    summary = summarize(_records(truth), truth, settings)
    assert summary.startswith(
        "# Notice reading run\n\n## Settings\n\n"
        "- commit: abc1234\n- reader: vlm\n- model: m\n- date: 2026-10-23\n\n## Results\n"
    )


def test_summary_counts_a_confident_wrong_value_in_its_row(truth):
    def mutate(name, row):
        if name == "pdf/notice-010.pdf":
            return make_reading(row, total_income_cents=1)
        return make_reading(row)

    summary = summarize(_records(truth, mutate), truth, SETTINGS)
    assert _table_row(summary, "total income").endswith("| 1 |")
    assert _table_row(summary, "name").endswith("| 0 |")


def test_summary_for_perfect_run_shows_100_percent_and_no_confident_wrong(truth):
    summary = summarize(_records(truth), truth, SETTINGS)
    for label in ("name", "address", "tax year", "total income", "notice date"):
        row = _table_row(summary, label)
        assert row.count("100.0%") == 3
        assert row.endswith("| 0 |")
    assert "notice-050 outcome: 8 field(s) at confidence >= 0.90" in summary


def test_summary_notice_050_line_is_n_a_when_the_unreadable_photo_was_not_run(truth):
    dev = {name: row for name, row in truth.items() if name in DEV_FILES}
    summary = summarize(_records(dev), truth, SETTINGS)
    assert "- notice-050 outcome: n/a" in summary.splitlines()


def test_unscored_run_lists_confident_fields_per_file():
    reading = NoticeReading(
        full_name=ReadField("A B", 0.95),
        street_number=ReadField("1", 0.5),
        street_name=ReadField(None, 0.0),
        unit=ReadField("", 0.9),
        postal_code=ReadField("H1H 1H1", 0.1),
        tax_year=ReadField(2025, 0.99),
        total_income_cents=ReadField(5, 0.2),
        notice_date=ReadField(dt.date(2026, 3, 28), 0.1),
    )
    records = [
        RunRecord("other/real-sample.pdf", reading, 1.0, None, 0.0),
        RunRecord("other/failed.pdf", None, 1.0, "DocumentReadError", 0.0),
    ]
    summary = summarize(records, {}, SETTINGS)
    assert "- other/real-sample.pdf: full_name, unit, tax_year" in summary
    assert "- other/failed.pdf: none" in summary
    assert "| name |" not in summary
