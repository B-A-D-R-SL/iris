# AI contribution: 50% or more AI-generated
"""Turns a Document Intelligence `prebuilt-layout` result into a NoticeReading.

The parser keys on labels that real notices also print (envelope window, `Date de l'avis :`,
`Année d'imposition`, the `Détail des calculs` table), not on the mock generator's quirks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from fields import (
    normalize_postal_code,
    normalize_unit,
    parse_amount_cents,
    parse_french_date,
    strip_accents,
)
from reader import UNREAD, NoticeReading, ReadField

# Postal-code shaped, not validated: OCR can misread one character (3Z0 as 320), and the
# name and street above it should still be read; the code itself is then left unread.
_POSTAL_LINE = re.compile(r"\(Qu[ée]bec\)\s+([A-Za-z0-9]{3}\s?[A-Za-z0-9]{3})\s*$")
_TAX_YEAR = re.compile(r"Ann[ée]e d['’]imposition\s+(\d{4})")
# Possessive \s*+ cannot backtrack; page footers print the label without a colon
_DATE_LABEL = re.compile(r"Date de l['’]avis\s*+(?::\s*+)?(.*)$")
_INCOME_LINE = "199"
_ASSESSED_HEADER = "etabli"  # "Montant établi", compared without accents and case
SHAPE_ERROR = "unexpected AnalyzeResult shape"

_Word = tuple[int, int, float]  # start, end, confidence


@dataclass(frozen=True)
class LayoutLine:
    """One printed line; `words` are (start, end, confidence) offsets within `text`."""

    text: str
    words: tuple[_Word, ...]

    def confidence(self, start: int = 0, end: int | None = None) -> float:
        """Lowest word confidence among the words overlapping [start, end); 0.0 if none."""
        stop = len(self.text) if end is None else end
        found = [conf for w_start, w_end, conf in self.words if w_start < stop and w_end > start]
        return min(found, default=0.0)


@dataclass(frozen=True)
class LayoutCell:
    """One table cell with the lowest confidence of the words inside it."""

    row: int
    column: int
    text: str
    confidence: float
    is_header: bool


@dataclass(frozen=True)
class LayoutDocument:
    """The lines (reading order, all pages) and tables of an analyzed document."""

    lines: tuple[LayoutLine, ...]
    tables: tuple[tuple[LayoutCell, ...], ...]

    @classmethod
    def from_analyze_result(cls, result: dict[str, Any]) -> LayoutDocument:
        """Convert the raw AnalyzeResult dict; ValueError when it does not have that shape."""
        try:
            pages = result.get("pages") or []
            words = [
                (w["span"]["offset"], w["span"]["length"], float(w["confidence"]))
                for page in pages
                for w in page.get("words") or []
            ]
            lines = tuple(_line(raw, words) for page in pages for raw in page.get("lines") or [])
            tables = tuple(
                tuple(_cell(raw, words) for raw in table.get("cells") or [])
                for table in result.get("tables") or []
            )
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            raise ValueError(SHAPE_ERROR) from exc
        return cls(lines, tables)


def _inside(offset: int, spans: list[dict[str, int]]) -> bool:
    """True when the offset falls inside any of the spans."""
    return any(s["offset"] <= offset < s["offset"] + s["length"] for s in spans)


def _line(raw: dict[str, Any], words: list[tuple[int, int, float]]) -> LayoutLine:
    """Build a LayoutLine from a raw line, keeping the words whose offsets lie in its spans."""
    spans = raw["spans"]
    base = spans[0]["offset"]
    inside = tuple(
        (offset - base, offset + length - base, conf)
        for offset, length, conf in words
        if _inside(offset, spans)
    )
    return LayoutLine(raw["content"], inside)


def _cell(raw: dict[str, Any], words: list[tuple[int, int, float]]) -> LayoutCell:
    """Build a LayoutCell from a raw cell with the lowest confidence of the words inside it."""
    spans = raw.get("spans") or []
    found = [conf for offset, _, conf in words if _inside(offset, spans)]
    return LayoutCell(
        row=raw["rowIndex"],
        column=raw["columnIndex"],
        text=raw["content"].strip(),
        confidence=min(found, default=0.0),
        is_header=raw.get("kind") == "columnHeader",
    )


def _street_parts(street_line: LayoutLine) -> list[tuple[str, int, int]]:
    """Split on ", " keeping each part's (text, start, end) within the line."""
    parts: list[tuple[str, int, int]] = []
    position = 0
    for part in street_line.text.split(", "):
        parts.append((part, position, position + len(part)))
        position += len(part) + 2
    return parts


def _unit_of(part: str) -> str | None:
    """The unit when a street-line part is a marker plus a value (`app. 106`), else None."""
    unit = normalize_unit(part)
    return unit if unit and unit != part.strip() else None


def _address_fields(
    postal_line: LayoutLine, street_line: LayoutLine, postal: str
) -> dict[str, ReadField]:
    """Postal code, street number, street name and unit read from the two address lines."""
    start = postal_line.text.rindex(postal)
    code = normalize_postal_code(postal)
    fields = {
        "postal_code": ReadField(code, postal_line.confidence(start, start + len(postal)))
        if code
        else UNREAD
    }
    parts = _street_parts(street_line)
    if len(parts) < 2:
        return fields
    unit = _unit_of(parts[-1][0]) if len(parts) > 2 else None
    name_parts = parts[1:-1] if unit else parts[1:]
    fields["street_number"] = ReadField(parts[0][0], street_line.confidence(0, parts[0][2]))
    fields["street_name"] = ReadField(
        ", ".join(text for text, _, _ in name_parts),
        street_line.confidence(name_parts[0][1], name_parts[-1][2]),
    )
    fields["unit"] = (
        ReadField(unit, street_line.confidence(parts[-1][1], parts[-1][2]))
        if unit
        else ReadField("", street_line.confidence())
    )
    return fields


def _envelope_fields(doc: LayoutDocument) -> dict[str, ReadField]:
    """Name and address: the two lines directly above `Montréal (Québec)  H2X 4N1`."""
    for index, line in enumerate(doc.lines):
        match = _POSTAL_LINE.search(line.text)
        if match and index >= 2:
            name_line, street_line = doc.lines[index - 2], doc.lines[index - 1]
            fields = {"full_name": ReadField(name_line.text.strip(), name_line.confidence())}
            return fields | _address_fields(line, street_line, match.group(1))
    return {}


def _tax_year(doc: LayoutDocument) -> ReadField[int]:
    """The tax year from the first line that states it; UNREAD if none does."""
    for line in doc.lines:
        match = _TAX_YEAR.search(line.text)
        if match:
            return ReadField(int(match.group(1)), line.confidence(*match.span(1)))
    return UNREAD


def _notice_date(doc: LayoutDocument) -> ReadField:
    """The first date after a `Date de l'avis` label, on the same line or the next one."""
    for index, line in enumerate(doc.lines):
        match = _DATE_LABEL.search(line.text)
        if not match:
            continue
        if match.group(1).strip():
            source, (start, end) = line, match.span(1)
        elif index + 1 < len(doc.lines):
            source = doc.lines[index + 1]
            start, end = 0, len(source.text)
        else:
            continue
        value = parse_french_date(source.text[start:end])
        if value is not None:
            return ReadField(value, source.confidence(start, end))
    return UNREAD


def _assessed_column(table: tuple[LayoutCell, ...]) -> int | None:
    """Index of the `Montant établi` column from its header cell, None if there is none."""
    for cell in table:
        header = cell.is_header or cell.row == 0
        if header and _ASSESSED_HEADER in strip_accents(cell.text).casefold():
            return cell.column
    return None


def _amount_in(text: str) -> int | None:
    """The one amount in a cell; other lines (watermark text OCR put in the cell) are ignored."""
    amounts = [
        cents for part in text.splitlines() if (cents := parse_amount_cents(part)) is not None
    ]
    return amounts[0] if len(amounts) == 1 else None


def _total_income(doc: LayoutDocument) -> ReadField[int]:
    """Line 199 in the `Montant établi` column (not `Montant déclaré`)."""
    for table in doc.tables:
        column = _assessed_column(table)
        if column is None:
            continue
        rows = {c.row for c in table if c.column == 0 and c.text == _INCOME_LINE}
        for cell in table:
            if cell.row in rows and cell.column == column:
                cents = _amount_in(cell.text)
                if cents is not None:
                    return ReadField(cents, cell.confidence)
    return UNREAD


def parse_layout(doc: LayoutDocument) -> NoticeReading:
    """Read the notice fields from a layout; a field not found is UNREAD."""
    envelope = _envelope_fields(doc)
    return NoticeReading(
        full_name=envelope.get("full_name", UNREAD),
        street_number=envelope.get("street_number", UNREAD),
        street_name=envelope.get("street_name", UNREAD),
        unit=envelope.get("unit", UNREAD),
        postal_code=envelope.get("postal_code", UNREAD),
        tax_year=_tax_year(doc),
        total_income_cents=_total_income(doc),
        notice_date=_notice_date(doc),
    )
