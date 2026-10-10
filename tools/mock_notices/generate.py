# AI contribution: 50% or more AI-generated
"""Generate fake Revenu Québec notices of assessment for Iris (SET-09).

Every notice is fictional and carries the SPECIMEN watermark. The spec is
docs/04-data/mock-notices-of-assessment.md. Run from this folder:

    uv run generate.py                 # writes to <repo>/mock-data/notices
    uv run generate.py --out some/dir

Writes pdf/*.pdf, photos/*.png (photos.py), truth.csv (what is printed on each
file) and applicants.csv (what the household declared at registration).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import random
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from faker import Faker
from reportlab.lib.colors import Color, HexColor, black
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

from photos import phone_photo

SEED = 42
CURRENT_TAX_YEAR = 2025
OLD_TAX_YEAR = 2023
WATERMARK = "SPÉCIMEN – DOCUMENT FICTIF – NE PAS UTILISER"
MASKED_SIN = "XXX XXX XXX"
DEFAULT_OUT = Path(__file__).resolve().parents[2] / "mock-data" / "notices"

# Real Montréal street names; civic numbers and postal codes are made up.
MONTREAL_STREETS = (
    "rue Saint-Denis",
    "boulevard Saint-Laurent",
    "rue Sherbrooke Est",
    "avenue du Mont-Royal Est",
    "rue Ontario Est",
    "rue Jean-Talon Est",
    "boulevard Pie-IX",
    "rue Beaubien Est",
    "rue Wellington",
    "rue Notre-Dame Ouest",
    "avenue Papineau",
    "rue Fleury Est",
    "boulevard Henri-Bourassa Est",
    "rue Sainte-Catherine Est",
    "boulevard de Maisonneuve Ouest",
    "avenue Van Horne",
    "chemin de la Côte-des-Neiges",
    "rue Jarry Est",
    "avenue Christophe-Colomb",
    "rue Masson",
    "rue Hochelaga",
    "boulevard Décarie",
    "avenue Somerled",
    "rue Saint-Hubert",
    "rue Bélanger",
    "rue Villeray",
    "avenue De Lorimier",
    "rue Rachel Est",
    "rue Saint-Zotique Est",
    "boulevard Rosemont",
    "boulevard Monk",
    "boulevard Saint-Michel",
    "rue Sauvé Est",
    "avenue Bennett",
    "rue Dandurand",
    "avenue Laurier Est",
    "rue Fullum",
    "rue de Bordeaux",
    "avenue Querbes",
    "rue Lajeunesse",
)
# Letters Canada Post uses in postal codes (no D, F, I, O, Q, U).
POSTAL_LETTERS = "ABCEGHJKLMNPRSTVWXYZ"

# File number -> case. Counts follow docs/04-data/mock-notices-of-assessment.md.
CASES: dict[int, str] = (
    {number: "clean" for number in range(1, 31)}
    | {number: "photo" for number in range(31, 46)}
    | {46: "old_tax_year", 47: "name_mismatch", 48: "address_mismatch", 49: "zero_income"}
    | {50: "unreadable"}
)
PHOTO_CASES = frozenset({"photo", "unreadable"})

# Clean files whose declared name differs in a way the name check must tolerate
# (business rules: case and accents ignored, extra middle names allowed).
MIDDLE_NAME_NUMBERS = (5, 20)
UPPERCASE_NUMBERS = (8, 25)
ACCENT_CONTROLS = 2

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


@dataclass(frozen=True)
class Declared:
    """What the household declared at registration for the person on a notice."""

    first_name: str
    last_name: str
    street_number: str
    street_name: str
    unit: str
    postal_code: str
    name_should_match: bool = True
    address_should_match: bool = True
    variation: str = "none"


@dataclass(frozen=True)
class Notice:
    """The values printed on one notice (amounts in cents) and what was declared."""

    number: int
    first_name: str
    last_name: str
    street_number: str
    street_name: str
    unit: str
    postal_code: str
    tax_year: int
    notice_date: dt.date
    total_income_cents: int
    net_income_cents: int
    taxable_income_cents: int
    balance_cents: int  # > 0: amount owed, < 0: refund
    case: str
    declared: Declared

    @property
    def stem(self) -> str:
        return f"notice-{self.number:03d}"

    @property
    def is_photo(self) -> bool:
        return self.case in PHOTO_CASES

    @property
    def file(self) -> str:
        """Path relative to the output folder."""
        return f"photos/{self.stem}.png" if self.is_photo else f"pdf/{self.stem}.pdf"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def _postal_code(rng: random.Random) -> str:
    letter = lambda: rng.choice(POSTAL_LETTERS)  # noqa: E731
    return f"H{rng.randint(1, 9)}{letter()} {rng.randint(0, 9)}{letter()}{rng.randint(0, 9)}"


def _unit(rng: random.Random) -> str:
    if rng.random() >= 0.4:
        return ""
    return str(rng.randint(1, 8)) if rng.random() < 0.5 else str(rng.randint(101, 412))


def _total_income_cents(rng: random.Random) -> int:
    # Mostly below the low-income cut-offs, some well above (draft: 0 to 85,000 $).
    dollars = rng.randint(4_000, 38_000) if rng.random() < 0.8 else rng.randint(38_000, 85_000)
    return dollars * 100 + rng.randint(0, 99)


def _notice_date(rng: random.Random, tax_year: int) -> dt.date:
    # Notices arrive between March 1 and June 30 of the following year.
    return dt.date(tax_year + 1, 3, 1) + dt.timedelta(days=rng.randint(0, 121))


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _other_last_name(fake: Faker, last_name: str) -> str:
    while True:
        other = fake.last_name()
        if strip_accents(other).casefold() != strip_accents(last_name).casefold():
            return other


def _moved(declared: Declared, rng: random.Random) -> Declared:
    """The household moved: another civic number, street, unit and postal code."""
    street_number, postal_code = declared.street_number, declared.postal_code
    while street_number == declared.street_number:
        street_number = str(rng.randint(100, 9999))
    while postal_code == declared.postal_code:
        postal_code = _postal_code(rng)
    return replace(
        declared,
        street_number=street_number,
        street_name=rng.choice(MONTREAL_STREETS),
        unit=_unit(rng),
        postal_code=postal_code,
        address_should_match=False,
        variation="moved",
    )


def make_notice(number: int, case: str, fake: Faker, rng: random.Random) -> Notice:
    first_name, last_name = fake.first_name(), fake.last_name()
    street_number, street_name = str(rng.randint(100, 9999)), rng.choice(MONTREAL_STREETS)
    unit, postal_code = _unit(rng), _postal_code(rng)
    tax_year = OLD_TAX_YEAR if case == "old_tax_year" else CURRENT_TAX_YEAR

    total = _total_income_cents(rng)
    net = round(total * (1 - rng.uniform(0, 0.15)))
    taxable = round(net * (1 - rng.uniform(0, 0.05)))
    balance = -rng.randint(0, 2_000_00) if rng.random() < 0.7 else rng.randint(1, 1_500_00)
    if case == "zero_income":
        total = net = taxable = balance = 0

    declared = Declared(first_name, last_name, street_number, street_name, unit, postal_code)
    if case == "name_mismatch":
        declared = replace(
            declared,
            last_name=_other_last_name(fake, last_name),
            name_should_match=False,
            variation="different_last_name",
        )
    elif case == "address_mismatch":
        declared = _moved(declared, rng)

    return Notice(
        number=number,
        first_name=first_name,
        last_name=last_name,
        street_number=street_number,
        street_name=street_name,
        unit=unit,
        postal_code=postal_code,
        tax_year=tax_year,
        notice_date=_notice_date(rng, tax_year),
        total_income_cents=total,
        net_income_cents=net,
        taxable_income_cents=taxable,
        balance_cents=balance,
        case=case,
        declared=declared,
    )


def _add_name_controls(notices: list[Notice], fake: Faker) -> list[Notice]:
    """Clean files where the declared name differs but must still match."""
    by_number = {notice.number: notice for notice in notices}

    for number in MIDDLE_NAME_NUMBERS:
        notice = by_number[number]
        middle = fake.first_name()
        while middle == notice.first_name:
            middle = fake.first_name()
        by_number[number] = replace(
            notice,
            first_name=f"{notice.first_name} {middle}",
            declared=replace(notice.declared, variation="middle_name_omitted"),
        )

    for number in UPPERCASE_NUMBERS:
        notice = by_number[number]
        by_number[number] = replace(
            notice,
            declared=replace(
                notice.declared,
                first_name=notice.first_name.upper(),
                last_name=notice.last_name.upper(),
                variation="uppercase",
            ),
        )

    accented = [
        notice
        for notice in by_number.values()
        if notice.case == "clean"
        and notice.declared.variation == "none"
        and strip_accents(notice.first_name + notice.last_name)
        != notice.first_name + notice.last_name
    ][:ACCENT_CONTROLS]
    if len(accented) < ACCENT_CONTROLS:
        raise RuntimeError("Not enough accented names for the accent controls; change the seed")
    for notice in accented:
        by_number[notice.number] = replace(
            notice,
            declared=replace(
                notice.declared,
                first_name=strip_accents(notice.first_name),
                last_name=strip_accents(notice.last_name),
                variation="accents_stripped",
            ),
        )

    return [by_number[number] for number in sorted(by_number)]


def build_notices(seed: int = SEED) -> list[Notice]:
    """Build every notice. Same seed, same notices."""
    fake = Faker("fr_CA")
    fake.seed_instance(seed)
    rng = random.Random(seed)
    notices = [make_notice(number, case, fake, rng) for number, case in CASES.items()]
    return _add_name_controls(notices, fake)


# ---------------------------------------------------------------------------
# PDF layout
# ---------------------------------------------------------------------------

PAGE_WIDTH, PAGE_HEIGHT = LETTER
MARGIN = 54
GREY = HexColor("#555555")
LIGHT_GREY = HexColor("#E6E6E6")
WATERMARK_RED = Color(0.75, 0.05, 0.05, alpha=0.22)


def format_amount(cents: int) -> str:
    """23456,78 $ in the French Canadian style: '23 456,78 $'."""
    dollars, rest = divmod(abs(cents), 100)
    return f"{dollars:,}".replace(",", " ") + f",{rest:02d} $"


def format_address_line(notice: Notice) -> str:
    line = f"{notice.street_number}, {notice.street_name}"
    return f"{line}, app. {notice.unit}" if notice.unit else line


def _label_value(pdf: Canvas, x: float, y: float, label: str, value: str) -> None:
    pdf.setFillColor(GREY)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(x, y, label)
    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x, y - 14, value)


def _paragraph(pdf: Canvas, x: float, y: float, text: str, width: float) -> float:
    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 9)
    for line in simpleSplit(text, "Helvetica", 9, width):
        pdf.drawString(x, y, line)
        y -= 12
    return y


def _draw_notice(pdf: Canvas, notice: Notice) -> None:
    right = PAGE_WIDTH - MARGIN
    content_width = right - MARGIN

    # Header
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(MARGIN, 738, "Revenu Québec")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(MARGIN, 712, "Avis de cotisation – Impôt sur le revenu")
    pdf.setLineWidth(1)
    pdf.line(MARGIN, 700, right, 700)

    # Taxpayer block (left) and notice block (right)
    _label_value(pdf, MARGIN, 680, "Nom, prénom", f"{notice.last_name}, {notice.first_name}")
    pdf.setFillColor(GREY)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(MARGIN, 644, "Adresse")
    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(MARGIN, 630, format_address_line(notice))
    pdf.drawString(MARGIN, 616, f"Montréal (Québec)  {notice.postal_code}")

    box_x = 372
    pdf.setStrokeColor(GREY)
    pdf.rect(box_x - 10, 596, right - box_x + 10, 98, stroke=1, fill=0)
    _label_value(pdf, box_x, 680, "Année d'imposition", str(notice.tax_year))
    _label_value(pdf, box_x, 648, "Date de l'avis", notice.notice_date.isoformat())
    _label_value(pdf, box_x, 616, "Numéro d'assurance sociale", MASKED_SIN)

    # Explanation
    y = _paragraph(
        pdf,
        MARGIN,
        568,
        f"Nous avons établi votre cotisation pour l'année d'imposition {notice.tax_year} à "
        "partir des renseignements fournis dans votre déclaration de revenus. Conservez cet "
        "avis : il peut vous être demandé comme preuve de revenu.",
        content_width,
    )

    # Summary lines
    y -= 16
    pdf.setFillColor(LIGHT_GREY)
    pdf.rect(MARGIN, y - 6, content_width, 20, stroke=0, fill=1)
    pdf.setFillColor(black)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(MARGIN + 6, y, "Sommaire de la cotisation")
    pdf.drawRightString(right - 6, y, "Montant")
    rows = [
        ("Revenu total (ligne 199)", notice.total_income_cents),
        ("Revenu net (ligne 275)", notice.net_income_cents),
        ("Revenu imposable (ligne 299)", notice.taxable_income_cents),
    ]
    if notice.balance_cents > 0:
        rows.append(("Impôt du Québec à payer", notice.balance_cents))
    elif notice.balance_cents < 0:
        rows.append(("Remboursement", notice.balance_cents))
    else:
        rows.append(("Solde", 0))
    pdf.setFont("Helvetica", 10)
    for label, cents in rows:
        y -= 24
        pdf.drawString(MARGIN + 6, y, label)
        pdf.drawRightString(right - 6, y, format_amount(cents))
        pdf.setStrokeColor(LIGHT_GREY)
        pdf.line(MARGIN, y - 8, right, y - 8)

    _paragraph(
        pdf,
        MARGIN,
        y - 40,
        "Si vous êtes en désaccord avec cette cotisation, vous pouvez présenter une "
        "opposition dans les 90 jours suivant la date de cet avis.",
        content_width,
    )


def _draw_watermark(pdf: Canvas, page: int, pages: int) -> None:
    """Diagonal watermark across the page plus a footer line."""
    pdf.saveState()
    pdf.setFillColor(WATERMARK_RED)
    pdf.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
    pdf.rotate(52)
    pdf.setFont("Helvetica-Bold", 46)
    pdf.drawCentredString(0, 20, "SPÉCIMEN – DOCUMENT FICTIF")
    pdf.drawCentredString(0, -40, "NE PAS UTILISER")
    pdf.restoreState()

    pdf.setFillColor(HexColor("#B00000"))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(PAGE_WIDTH / 2, 36, WATERMARK)
    pdf.setFillColor(GREY)
    pdf.setFont("Helvetica", 8)
    pdf.drawRightString(PAGE_WIDTH - MARGIN, 36, f"Page {page} de {pages}")


def render_pdf(notice: Notice) -> bytes:
    """One-page notice. invariant=True keeps the bytes identical between runs."""
    buffer = io.BytesIO()
    pdf = Canvas(buffer, pagesize=LETTER, invariant=True)
    pdf.setTitle(f"Avis de cotisation {notice.tax_year} – {WATERMARK}")
    pdf.setAuthor("Iris mock notice generator")
    _draw_notice(pdf, notice)
    _draw_watermark(pdf, page=1, pages=1)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


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
    for folder, pattern in (("pdf", "notice-*.pdf"), ("photos", "notice-*.png")):
        (out / folder).mkdir(parents=True, exist_ok=True)
        for stale in (out / folder).glob(pattern):
            stale.unlink()

    notices = build_notices(seed)
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
