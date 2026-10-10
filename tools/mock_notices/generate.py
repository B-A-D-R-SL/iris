# AI contribution: 50% or more AI-generated
"""Generate fake Revenu Québec notices of assessment for Iris (SET-09).

Every notice is fictional and carries the SPECIMEN watermark. The spec is
docs/04-data/mock-notices-of-assessment.md. Run from this folder:

    uv run generate.py                 # writes to <repo>/mock-data/notices
    uv run generate.py --out some/dir

Notices 031 to 045 are delivered as phone photos (photos.py) instead of PDFs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import random
from dataclasses import dataclass
from pathlib import Path

from faker import Faker
from reportlab.lib.colors import Color, HexColor, black
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

from photos import phone_photo

SEED = 42
NOTICE_COUNT = 50
PHOTO_NUMBERS = range(31, 46)
CURRENT_TAX_YEAR = 2025
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


@dataclass(frozen=True)
class Notice:
    """The values printed on one notice. Amounts are in cents."""

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

    @property
    def stem(self) -> str:
        return f"notice-{self.number:03d}"

    @property
    def is_photo(self) -> bool:
        return self.number in PHOTO_NUMBERS

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


def make_notice(number: int, fake: Faker, rng: random.Random) -> Notice:
    total = _total_income_cents(rng)
    net = round(total * (1 - rng.uniform(0, 0.15)))
    taxable = round(net * (1 - rng.uniform(0, 0.05)))
    balance = -rng.randint(0, 2_000_00) if rng.random() < 0.7 else rng.randint(1, 1_500_00)
    return Notice(
        number=number,
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        street_number=str(rng.randint(100, 9999)),
        street_name=rng.choice(MONTREAL_STREETS),
        unit=_unit(rng),
        postal_code=_postal_code(rng),
        tax_year=CURRENT_TAX_YEAR,
        notice_date=_notice_date(rng, CURRENT_TAX_YEAR),
        total_income_cents=total,
        net_income_cents=net,
        taxable_income_cents=taxable,
        balance_cents=balance,
    )


def build_notices(seed: int = SEED) -> list[Notice]:
    """Build every notice. Same seed, same notices."""
    fake = Faker("fr_CA")
    fake.seed_instance(seed)
    rng = random.Random(seed)
    return [make_notice(number, fake, rng) for number in range(1, NOTICE_COUNT + 1)]


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
            phone_photo(pdf_bytes, rng).save(out / notice.file, optimize=True)
        else:
            (out / notice.file).write_bytes(pdf_bytes)
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
