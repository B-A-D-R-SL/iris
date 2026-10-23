# AI contribution: 50% or more AI-generated
"""Checks the French field parsers."""

from __future__ import annotations

import datetime as dt

import pytest

from fields import normalize_postal_code, parse_amount_cents, parse_french_date


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("23 456,78", 2345678),
        ("23 456,78 $", 2345678),
        ("23 456,78", 2345678),
        ("23 456,78", 2345678),
        ("0,00", 0),
        ("1 200", 120000),
        ("5,5", 550),
    ],
)
def test_parse_amount_cents_reads_french_amounts(text, cents):
    assert parse_amount_cents(text) == cents


@pytest.mark.parametrize("text", ["", "abc", "23.456,78,9", "12,345", "$"])
def test_parse_amount_cents_rejects_garbage(text):
    assert parse_amount_cents(text) is None


@pytest.mark.parametrize(
    ("text", "date"),
    [
        ("28 mars 2026", dt.date(2026, 3, 28)),
        ("1er avril 2026", dt.date(2026, 4, 1)),
        ("15 février 2026", dt.date(2026, 2, 15)),
        ("15 fevrier 2026", dt.date(2026, 2, 15)),
        ("3 août 2026", dt.date(2026, 8, 3)),
        ("  3 AOUT 2026 ", dt.date(2026, 8, 3)),
    ],
)
def test_parse_french_date(text, date):
    assert parse_french_date(text) == date


@pytest.mark.parametrize("text", ["31 février 2026", "", "2026-03-28x", "5 marzo 2026"])
def test_parse_french_date_rejects_invalid(text):
    assert parse_french_date(text) is None


def test_normalize_postal_code():
    assert normalize_postal_code("h2x4n1") == "H2X 4N1"
    assert normalize_postal_code(" H2X 4N1 ") == "H2X 4N1"
    assert normalize_postal_code("H2X 4N") is None
