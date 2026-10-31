# AI contribution: 50% or more AI-generated
"""Scores readings against mock-data/notices/truth.csv and renders the Markdown summary."""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

from fields import strip_accents
from reader import NoticeReading
from records import RunRecord

CONFIDENT = 0.90  # the business rules' automatic-approval confidence

CORRECT = "correct"
WRONG = "wrong"
MISSING = "missing"

FIELD_NAMES = tuple(field.name for field in dataclasses.fields(NoticeReading))
ADDRESS_FIELDS = ("street_number", "street_name", "unit", "postal_code")
_NORMALIZED_FIELDS = ("full_name", "street_name")  # compared like the business-rule name check

DEV_FILES = frozenset(
    [f"pdf/notice-{number:03d}.pdf" for number in range(1, 6)]
    + [f"photos/notice-{number:03d}.png" for number in range(31, 34)]
)
CHANGED_RETURN_STEMS = frozenset(f"notice-{number:03d}" for number in (3, 11, 17, 24, 29, 34, 41))
UNREADABLE_CASE = "unreadable"

# Summary rows: label and the reading fields that must all be correct.
_ROWS = (
    ("name", ("full_name",)),
    ("address", ADDRESS_FIELDS),
    ("tax year", ("tax_year",)),
    ("total income", ("total_income_cents",)),
    ("notice date", ("notice_date",)),
)

_NOTICE_NUMBER = re.compile(r"(?<![A-Z0-9])[QM](?=[A-Z0-9]*\d)[A-Z0-9]{10}(?![A-Z0-9])")
_CONTROL_NUMBER = re.compile(r"(?<!\d)\d{11}(?!\d)")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class TruthRow:
    """What is printed on one mock notice (one row of truth.csv)."""

    file: str
    first_name: str
    last_name: str
    street_number: str
    street_name: str
    unit: str
    postal_code: str
    tax_year: int
    total_income_cents: int
    notice_date: dt.date
    case: str

    @property
    def expected(self) -> dict[str, object]:
        """The value a reader should return for each field of NoticeReading."""
        return {
            "full_name": f"{self.first_name} {self.last_name}",
            "street_number": self.street_number,
            "street_name": self.street_name,
            "unit": self.unit,
            "postal_code": self.postal_code,
            "tax_year": self.tax_year,
            "total_income_cents": self.total_income_cents,
            "notice_date": self.notice_date,
        }


@dataclass(frozen=True)
class FileScore:
    """The outcome of each field of one reading, and the fields that were confidently wrong."""

    outcomes: dict[str, str]
    confident_wrong_fields: tuple[str, ...]

    def all_correct(self, fields: tuple[str, ...]) -> bool:
        """True when every listed field was read correctly."""
        return all(self.outcomes[name] == CORRECT for name in fields)


def load_truth(path: Path) -> dict[str, TruthRow]:
    """Read truth.csv, keyed by `file` (for example `pdf/notice-003.pdf`)."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = [
            TruthRow(
                file=row["file"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                street_number=row["street_number"],
                street_name=row["street_name"],
                unit=row["unit"],
                postal_code=row["postal_code"],
                tax_year=int(row["tax_year"]),
                total_income_cents=int(row["total_income_cents"]),
                notice_date=dt.date.fromisoformat(row["notice_date"]),
                case=row["case"],
            )
            for row in csv.DictReader(handle)
        ]
    return {row.file: row for row in rows}


def _normalize(text: str) -> str:
    return _SPACES.sub(" ", strip_accents(text).casefold()).strip()


def _outcome(name: str, expected: object, value: object) -> str:
    """Score one field value against the expected one: correct, wrong or missing."""
    if value is None:
        return MISSING
    if name in _NORMALIZED_FIELDS:
        same = _normalize(str(value)) == _normalize(str(expected))
    else:
        same = value == expected
    return CORRECT if same else WRONG


def score_reading(truth: TruthRow, reading: NoticeReading | None) -> FileScore:
    """Compare a reading (None: the read failed) with the truth, field by field."""
    if reading is None:
        return FileScore({name: MISSING for name in FIELD_NAMES}, ())
    expected = truth.expected
    outcomes: dict[str, str] = {}
    confident_wrong: list[str] = []
    for name in FIELD_NAMES:
        field = getattr(reading, name)
        outcomes[name] = _outcome(name, expected[name], field.value)
        if outcomes[name] == WRONG and field.confidence >= CONFIDENT:
            confident_wrong.append(name)
    return FileScore(outcomes, tuple(confident_wrong))


def confident_fields(reading: NoticeReading | None) -> tuple[str, ...]:
    """Names of the fields returned at confidence >= CONFIDENT (needs no truth)."""
    if reading is None:
        return ()
    return tuple(
        name
        for name in FIELD_NAMES
        if getattr(reading, name).value is not None
        and getattr(reading, name).confidence >= CONFIDENT
    )


def contains_document_number(reading: NoticeReading) -> bool:
    """True when a text field holds a notice number (Q or M plus 10) or a control number."""
    for name in FIELD_NAMES:
        value = getattr(reading, name).value
        if isinstance(value, str) and (
            _NOTICE_NUMBER.search(value) or _CONTROL_NUMBER.search(value)
        ):
            return True
    return False


# --- Markdown summary -------------------------------------------------------------------------


def _percent(correct: int, total: int) -> str:
    """A percentage with its counts, or `n/a` when the total is zero."""
    return "n/a" if total == 0 else f"{100 * correct / total:.1f}% ({correct}/{total})"


def _accuracy(scores: list[FileScore], fields: tuple[str, ...]) -> str:
    """The share of scored files whose listed fields are all correct."""
    return _percent(sum(score.all_correct(fields) for score in scores), len(scores))


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _stem(file: str) -> str:
    return Path(file).stem


def _scored(
    records: list[RunRecord], truth: dict[str, TruthRow]
) -> list[tuple[RunRecord, TruthRow]]:
    """The records that have a truth row, each paired with it."""
    return [(record, truth[record.file]) for record in records if record.file in truth]


def _accuracy_table(pairs: list[tuple[RunRecord, TruthRow]]) -> list[str]:
    """Held-out PDFs and held-out photos measure the pass criteria; dev files only tune."""
    readable = [(r, t) for r, t in pairs if t.case != UNREADABLE_CASE]
    heldout = [(r, t) for r, t in readable if r.file not in DEV_FILES]

    def scores(selected: list[tuple[RunRecord, TruthRow]]) -> list[FileScore]:
        """The score of each selected record against its truth row."""
        return [score_reading(t, r.reading) for r, t in selected]

    groups = (
        scores([(r, t) for r, t in heldout if r.file.startswith("pdf/")]),
        scores([(r, t) for r, t in heldout if r.file.startswith("photos/")]),
        scores([(r, t) for r, t in readable if r.file in DEV_FILES]),
    )
    every = scores(pairs)
    lines = [
        "| Field | Held-out PDFs | Held-out photos | Dev (all) | Confident-and-wrong |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label, fields in _ROWS:
        cells = " | ".join(_accuracy(group, fields) for group in groups)
        bad = sum(any(f in s.confident_wrong_fields for f in fields) for s in every)
        lines.append(f"| {label} | {cells} | {bad} |")
    return lines


def _truth_lines(pairs: list[tuple[RunRecord, TruthRow]]) -> list[str]:
    """Summary lines for changed-return income accuracy and the unreadable notice."""
    changed = [
        score_reading(t, r.reading) for r, t in pairs if _stem(r.file) in CHANGED_RETURN_STEMS
    ]
    unreadable = [r for r, t in pairs if t.case == UNREADABLE_CASE]
    confident = sum(len(confident_fields(r.reading)) for r in unreadable)
    outcome = (
        f"{confident} field(s) at confidence >= {CONFIDENT:.2f} (pass: 0)" if unreadable else "n/a"
    )
    return [
        f"Changed returns, income accuracy ({len(changed)} files): "
        f"{_accuracy(changed, ('total_income_cents',))}",
        f"notice-050 outcome: {outcome}",
    ]


def _run_lines(records: list[RunRecord]) -> list[str]:
    """Summary lines for failures, document number leaks, time and cost."""
    leaks = sum(r.reading is not None and contains_document_number(r.reading) for r in records)
    seconds = [r.seconds for r in records]
    return [
        f"Failures: {sum(r.error is not None for r in records)}",
        f"document_number_leaks: {leaks}",
        f"Median seconds: {statistics.median(seconds):.1f}",
        f"p95 seconds: {_p95(seconds):.1f}",
        f"Mean cost per notice (USD): {statistics.fmean(r.cost_usd for r in records):.4f}",
    ]


def _unscored_lines(records: list[RunRecord]) -> list[str]:
    """Summary lines listing each file's confident fields, with no truth to score against."""
    lines = [
        f"Fields returned at confidence >= {CONFIDENT:.2f}, per file (no truth available):",
        "",
    ]
    for record in records:
        names = ", ".join(confident_fields(record.reading)) or "none"
        lines.append(f"- {record.file}: {names}")
    return lines


def summarize(
    records: list[RunRecord], truth: dict[str, TruthRow], settings: dict[str, str]
) -> str:
    """Render the run as Markdown: settings, accuracy table, pass-criteria measures, unscored."""
    pairs = _scored(records, truth)
    unscored = [record for record in records if record.file not in truth]
    sections: list[str] = ["# Notice reading run", "", "## Settings", ""]
    sections += [f"- {name}: {value}" for name, value in settings.items()]
    sections += ["", "## Results", ""]
    if records:
        if pairs:
            sections += _accuracy_table(pairs) + [""]
        lines = (_truth_lines(pairs) if pairs else []) + _run_lines(records)
        sections += [f"- {line}" for line in lines] + [""]
    if unscored:
        sections += _unscored_lines(unscored) + [""]
    return "\n".join(sections)
