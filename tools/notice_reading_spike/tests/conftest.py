# AI contribution: 50% or more AI-generated
"""Shared fixtures: the mock notices and helpers to build readings and truth rows."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from reader import NoticeReading, ReadField
from score import TruthRow, load_truth

NOTICES_DIR = Path(__file__).resolve().parents[3] / "mock-data" / "notices"


@pytest.fixture(scope="session")
def notices_dir() -> Path:
    return NOTICES_DIR


@pytest.fixture(scope="session")
def truth() -> dict[str, TruthRow]:
    return load_truth(NOTICES_DIR / "truth.csv")


def make_reading(row: TruthRow, confidence: float = 1.0, **overrides: object) -> NoticeReading:
    """The truth as a reading; `overrides` replace a field's value (same confidence)."""
    values: dict[str, object] = {
        "full_name": f"{row.first_name} {row.last_name}",
        "street_number": row.street_number,
        "street_name": row.street_name,
        "unit": row.unit,
        "postal_code": row.postal_code,
        "tax_year": row.tax_year,
        "total_income_cents": row.total_income_cents,
        "notice_date": row.notice_date,
    }
    values.update(overrides)
    return NoticeReading(**{name: ReadField(value, confidence) for name, value in values.items()})


def make_row(**overrides: object) -> TruthRow:
    values: dict[str, object] = {
        "file": "pdf/notice-099.pdf",
        "first_name": "Zoé Jessica",
        "last_name": "Lapointe",
        "street_number": "1924",
        "street_name": "boulevard Saint-Laurent",
        "unit": "",
        "postal_code": "H2X 4N1",
        "tax_year": 2025,
        "total_income_cents": 7517090,
        "notice_date": dt.date(2026, 3, 28),
        "case": "clean",
    }
    values.update(overrides)
    return TruthRow(**values)
