# AI contribution: 50% or more AI-generated
"""Generate fake Revenu Québec notices of assessment for Iris (SET-09).

Every notice is fictional and carries the SPECIMEN watermark. The spec is
docs/04-data/mock-notices-of-assessment.md. Run from this folder:

    uv run generate.py                 # writes to <repo>/mock-data/notices
    uv run generate.py --out some/dir

Writes pdf/*.pdf, photos/*.png (photos.py), truth.csv (what is printed on each
file) and applicants.csv (what the household declared at registration).

The notice data is built in notices.py (amounts in tax.py), laid out as a PDF
in layout.py and turned into a phone photo in photos.py.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from layout import render_pdf
from notices import SEED, Notice, build_notices
from photos import phone_photo

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "mock-data" / "notices"

TRUTH_COLUMNS = (
    "file",
    "first_name",
    "last_name",
    "street_number",
    "street_name",
    "unit",
    "postal_code",
    "tax_year",
    "total_income_cents",
    "notice_date",
    "case",
)
APPLICANT_COLUMNS = (
    "file",
    "first_name",
    "last_name",
    "street_number",
    "street_name",
    "unit",
    "postal_code",
    "name_should_match",
    "address_should_match",
    "variation",
)


# ---------------------------------------------------------------------------
# Truth and applicant files
# ---------------------------------------------------------------------------


def truth_row(notice: Notice) -> dict[str, str]:
    return {
        "file": notice.file,
        "first_name": notice.first_name,
        "last_name": notice.last_name,
        "street_number": notice.street_number,
        "street_name": notice.street_name,
        "unit": notice.unit,
        "postal_code": notice.postal_code,
        "tax_year": str(notice.tax_year),
        "total_income_cents": str(notice.total_income_cents),
        "notice_date": notice.notice_date.isoformat(),
        "case": notice.case,
    }


def applicant_row(notice: Notice) -> dict[str, str]:
    values = asdict(notice.declared)
    row = {"file": notice.file} | {key: str(value) for key, value in values.items()}
    for flag in ("name_should_match", "address_should_match"):
        row[flag] = "true" if values[flag] else "false"
    return row


def write_csv(path: Path, columns: tuple[str, ...], rows: Iterable[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def generate(out: Path, seed: int = SEED) -> list[Notice]:
    # Build first: a seed that cannot give every case fails before any file is deleted.
    notices = build_notices(seed)
    for folder, pattern in (("pdf", "notice-*.pdf"), ("photos", "notice-*.png")):
        (out / folder).mkdir(parents=True, exist_ok=True)
        for stale in (out / folder).glob(pattern):
            stale.unlink()

    for notice in notices:
        pdf_bytes = render_pdf(notice)
        if notice.is_photo:
            # Own random stream per photo, so photo effects never shift the notice data.
            rng = random.Random(f"{seed}-photo-{notice.number}")
            photo = phone_photo(pdf_bytes, rng, unreadable=notice.case == "unreadable")
            photo.save(out / notice.file, optimize=True)
        else:
            (out / notice.file).write_bytes(pdf_bytes)

    write_csv(out / "truth.csv", TRUTH_COLUMNS, map(truth_row, notices))
    write_csv(out / "applicants.csv", APPLICANT_COLUMNS, map(applicant_row, notices))
    return notices


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder")
    parser.add_argument("--seed", type=int, default=SEED, help="random seed (default 42)")
    args = parser.parse_args()
    notices = generate(args.out, args.seed)
    print(f"Wrote {len(notices)} notices to {args.out}")


if __name__ == "__main__":
    main()
