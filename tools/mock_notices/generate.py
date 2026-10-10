# AI contribution: 50% or more AI-generated
"""Generate fake Revenu Québec notices of assessment for Iris (SET-09).

Every notice is fictional and carries the SPECIMEN watermark. The spec is
docs/03-data/mock-notices-of-assessment.md. Run from this folder:

    uv run generate.py                 # writes to <repo>/mock-data/notices
    uv run generate.py --out some/dir

Writes pdf/*.pdf, photos/*.png (photos.py), truth.csv (what is printed on each
file) and applicants.csv (what the household declared at registration).

The two-page layout follows a redacted sample notice (tax year 2018) published
as an example: a cover page, then "Détail des calculs" with the declared and
the assessed amount of every TP-1 line. Line labels come from the 2025 TP-1.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import random
import string
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
FORM_CODE = "TPF-99 (SPÉCIMEN)"
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
FRENCH_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)

# File number -> case. Counts follow docs/03-data/mock-notices-of-assessment.md.
CASES: dict[int, str] = (
    {number: "clean" for number in range(1, 31)}
    | {number: "photo" for number in range(31, 46)}
    | {46: "old_tax_year", 47: "name_mismatch", 48: "address_mismatch", 49: "zero_income"}
    | {50: "unreadable"}
)
PHOTO_CASES = frozenset({"photo", "unreadable"})
# Notices where Revenu Québec changed the return: an income the person did not
# declare was added, so "Montant déclaré" and "Montant établi" differ.
ADJUSTED_NUMBERS = (3, 11, 17, 24, 29, 34, 41)

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

# TP-1 lines printed on the "Détail des calculs" page, in order. Labels are
# from the 2025 TP-1, shortened where the form adds instructions.
LINE_LABELS = {
    "101": "Revenus d'emploi",
    "111": "Prestations d'assurance emploi",
    "114": "Pension de sécurité de la vieillesse",
    "119": "Prestations du RRQ ou du RPC",
    "122": "Prestations d'un régime de retraite",
    "130": "Intérêts et autres revenus de placement",
    "147": "Prestations d'assistance sociale",
    "154": "Autres revenus",
    "199": "Revenu total",
    "201": "Déduction pour travailleur",
    "214": "Déduction pour REER ou RPAC/RVER",
    "250": "Autres déductions",
    "275": "Revenu net",
    "295": "Déductions pour certains revenus",
    "297": "Déductions diverses",
    "299": "Revenu imposable",
    "350": "Montant personnel de base",
    "377": "Montant des lignes 359 à 376",
    "377.1": "Montant de la ligne 377 multiplié par 14 %",
    "399": "Crédits d'impôt non remboursables",
    "401": "Impôt sur le revenu imposable",
    "406": "Crédits d'impôt non remboursables",
    "432": "Impôt",
    "450": "Impôt et cotisations",
    "451": "Impôt du Québec retenu à la source",
    "456": "Crédits d'impôt relatifs à la prime au travail",
    "462": "Autres crédits",
    "465": "Impôt payé et autres crédits",
    "478": "Remboursement",
    "479": "Solde à payer",
}
INCOME_LINES = ("101", "111", "114", "119", "122", "130", "147", "154")
DEDUCTION_LINES = ("201", "214", "250")
PAYMENT_LINES = ("451", "456", "462")
TOTAL_LINES = frozenset({"199", "275", "299", "399", "432", "450", "465", "478", "479"})
# Sign printed next to each line, as on the notice.
LINE_SIGNS = {"199": "=", "275": "=", "299": "=", "377": "=", "377.1": "=", "399": "="}
LINE_SIGNS |= {"401": "=", "406": "-", "432": "=", "450": "=", "465": "=", "478": "=", "479": "="}
LINE_SIGNS |= {line: "+" for line in INCOME_LINES} | {line: "-" for line in DEDUCTION_LINES}
LINE_SIGNS |= {"295": "-", "297": "-", "350": "", "451": "", "456": "+", "462": "+"}

# Simplified Québec tax: basic personal amount, 14 % credit, brackets (cents).
TAX_RULES = {
    2025: {"basic": 18_571_00, "brackets": ((53_255_00, 0.14), (106_495_00, 0.19))},
    2023: {"basic": 17_183_00, "brackets": ((49_275_00, 0.14), (98_540_00, 0.19))},
}
TOP_RATE = 0.24


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
    notice_number: str
    document_number: str
    direct_deposit: bool
    declared_lines: dict[str, int]  # "Montant déclaré" column
    assessed_lines: dict[str, int]  # "Montant établi" column
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

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def total_income_cents(self) -> int:
        """Line 199 as assessed by Revenu Québec: the value Iris must read."""
        return self.assessed_lines["199"]

    @property
    def balance_cents(self) -> int:
        """> 0: amount owed (line 479), < 0: refund (line 478)."""
        return self.assessed_lines.get("479", 0) - self.assessed_lines.get("478", 0)

    @property
    def is_adjusted(self) -> bool:
        return self.declared_lines != self.assessed_lines


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


def _notice_number(rng: random.Random) -> str:
    """11 letters or digits starting with Q or M, like a real notice number."""
    alphabet = string.ascii_uppercase + string.digits
    return rng.choice("QM") + "".join(rng.choice(alphabet) for _ in range(10))


def _split(rng: random.Random, total: int, lines: tuple[str, ...]) -> dict[str, int]:
    """Split a total (cents) over income lines; the parts add up exactly."""
    weights = [rng.uniform(0.2, 1.0) for _ in lines]
    parts = [round(total * weight / sum(weights)) for weight in weights[:-1]]
    return dict(zip(lines, [*parts, total - sum(parts)], strict=True))


def _income_lines(rng: random.Random, total: int) -> dict[str, int]:
    if total == 0:
        return {}
    profile = rng.choices(
        ("work", "work_ei", "retired", "assistance", "mixed"), weights=(35, 15, 20, 20, 10)
    )[0]
    lines = {
        "work": ("101",),
        "work_ei": ("101", "111"),
        "retired": ("114", "119", "122") if rng.random() < 0.3 else ("114", "119"),
        "assistance": ("147", "154") if rng.random() < 0.4 else ("147",),
        "mixed": ("101", "147"),
    }[profile]
    if rng.random() < 0.15:
        lines += ("130",)
    return _split(rng, total, lines)


def _income_tax(taxable: int, tax_year: int) -> int:
    tax, floor = 0.0, 0
    for ceiling, rate in TAX_RULES[tax_year]["brackets"]:
        tax += (min(taxable, ceiling) - floor) * rate if taxable > floor else 0
        floor = ceiling
    tax += max(0, taxable - floor) * TOP_RATE
    return round(tax)


def calculate(
    tax_year: int, income: dict[str, int], extra: dict[str, int], payments: dict[str, int]
) -> dict[str, int]:
    """One column of 'Détail des calculs'. `extra` holds 214, 250 and 297."""
    lines = {line: income[line] for line in INCOME_LINES if line in income}
    lines["199"] = sum(lines.values())
    worker = min(round(income.get("101", 0) * 0.06), 1_421_00)
    deductions = {"201": worker, "214": extra.get("214", 0), "250": extra.get("250", 0)}
    lines |= {line: amount for line, amount in deductions.items() if amount}
    lines["275"] = max(0, lines["199"] - sum(deductions.values()))
    # Social assistance is part of total income but not taxable (line 295).
    for line, amount in (("295", income.get("147", 0)), ("297", extra.get("297", 0))):
        if amount:
            lines[line] = amount
    lines["299"] = max(0, lines["275"] - lines.get("295", 0) - lines.get("297", 0))

    basic = TAX_RULES[tax_year]["basic"]
    lines |= {"350": basic, "377": basic, "377.1": round(basic * 0.14)}
    lines["399"] = lines["377.1"]
    lines["401"] = _income_tax(lines["299"], tax_year)
    lines["406"] = lines["399"]
    lines["432"] = max(0, lines["401"] - lines["406"])
    lines["450"] = lines["432"]
    lines |= {line: payments[line] for line in PAYMENT_LINES if payments.get(line)}
    lines["465"] = sum(payments.values())
    balance = lines["450"] - lines["465"]
    lines["479" if balance > 0 else "478"] = abs(balance)
    return lines


def _payments(rng: random.Random, income: dict[str, int], tax: int) -> dict[str, int]:
    payments = {}
    if any(line in income for line in ("101", "111", "119", "122")):
        payments["451"] = round(tax * rng.uniform(0.7, 1.5)) + rng.randint(0, 300_00)
    if 7_200_00 <= income.get("101", 0) <= 30_000_00:
        payments["456"] = rng.randint(100_00, 900_00)
    if income and rng.random() < 0.15:
        payments["462"] = rng.randint(50_00, 400_00)
    return payments


def _leave_out_a_slip(rng: random.Random, income: dict[str, int]) -> dict[str, int]:
    """Income as the person declared it: one slip left out, which Revenu Québec added back.

    `income` (the assessed income) is updated in place so its total stays the same.
    """
    line = "101" if "101" in income else "130"
    missing = min(rng.randint(150_00, 2_500_00), sum(income.values()) // 4)
    if line not in income:
        biggest = max(income, key=lambda key: income[key])
        income[biggest] -= missing
        income[line] = missing
    declared = dict(income)
    declared[line] -= missing
    return {key: value for key, value in declared.items() if value}


def _calculations(
    rng: random.Random, tax_year: int, total: int, adjusted: bool
) -> tuple[dict[str, int], dict[str, int]]:
    """(declared, assessed) columns. Assessed line 199 always equals `total`."""
    income = _income_lines(rng, total)
    declared_income = _leave_out_a_slip(rng, income) if adjusted and income else dict(income)

    extra = {}
    if income.get("101", 0) > 35_000_00 and rng.random() < 0.4:
        extra["214"] = rng.randint(500_00, 3_000_00)
    if income and rng.random() < 0.1:
        extra["250"] = rng.randint(100_00, 800_00)
    if income and rng.random() < 0.1:
        extra["297"] = rng.randint(50_00, 500_00)

    tax = calculate(tax_year, income, extra, {})["432"]
    payments = _payments(rng, income, tax)
    assessed = calculate(tax_year, income, extra, payments)
    return calculate(tax_year, declared_income, extra, payments), assessed


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
    total = 0 if case == "zero_income" else _total_income_cents(rng)
    declared_lines, assessed_lines = _calculations(
        rng, tax_year, total, adjusted=number in ADJUSTED_NUMBERS
    )

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
        notice_number=_notice_number(rng),
        document_number=str(rng.randint(10**10, 10**11 - 1)),
        direct_deposit=rng.random() < 0.8,
        declared_lines=declared_lines,
        assessed_lines=assessed_lines,
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
RIGHT = PAGE_WIDTH - MARGIN
PAGES = 2
GREY = HexColor("#555555")
TITLE_GREY = HexColor("#6B6B6B")
LIGHT_GREY = HexColor("#BBBBBB")
WATERMARK_RED = Color(0.75, 0.05, 0.05, alpha=0.22)


def format_amount(cents: int) -> str:
    """French Canadian style, as in the calculation table: '23 456,78'."""
    dollars, rest = divmod(abs(cents), 100)
    return f"{dollars:,}".replace(",", " ") + f",{rest:02d}"


def format_money(cents: int) -> str:
    """Amount with the dollar sign, as on the cover page: '23 456,78 $'."""
    return f"{format_amount(cents)} $"


def format_date(date: dt.date) -> str:
    """French long date, as on the notice: '28 mars 2026', '1er avril 2026'."""
    day = "1er" if date.day == 1 else str(date.day)
    return f"{day} {FRENCH_MONTHS[date.month - 1]} {date.year}"


def format_address_line(notice: Notice) -> str:
    line = f"{notice.street_number}, {notice.street_name}"
    return f"{line}, app. {notice.unit}" if notice.unit else line


def _text(pdf: Canvas, x: float, y: float, text: str, font: str = "Helvetica", size: float = 9):
    pdf.setFont(font, size)
    pdf.drawString(x, y, text)


def _paragraph(
    pdf: Canvas, x: float, y: float, text: str, width: float, font: str = "Helvetica"
) -> float:
    pdf.setFillColor(black)
    pdf.setFont(font, 9.5)
    for line in simpleSplit(text, font, 9.5, width):
        pdf.drawString(x, y, line)
        y -= 12
    return y - 8


def _page_header(pdf: Canvas, page: int) -> None:
    pdf.setFillColor(black)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawRightString(RIGHT, 760, FORM_CODE)
    pdf.drawRightString(RIGHT, 751, f"Page {page} de {PAGES}")


def _page_footer(pdf: Canvas, notice: Notice) -> None:
    """Identity box repeated at the bottom of every page, then the watermark line."""
    cells = (
        (MARGIN, 280, "Prénom et nom de famille", notice.full_name),
        (MARGIN + 280, 140, "Date de l'avis", format_date(notice.notice_date)),
        (RIGHT - 80, 80, "Année d'imposition", str(notice.tax_year)),
    )
    pdf.setStrokeColor(GREY)
    pdf.setLineWidth(0.6)
    for x, width, label, value in cells:
        pdf.rect(x, 92, width, 26, stroke=1, fill=0)
        pdf.setFillColor(black)
        _text(pdf, x + 4, 110, label, size=6.5)
        _text(pdf, x + 4, 97, value, "Helvetica-Bold", 9)

    pdf.setFillColor(HexColor("#B00000"))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(PAGE_WIDTH / 2, 60, WATERMARK)


def _diagonal_watermark(pdf: Canvas) -> None:
    pdf.saveState()
    pdf.setFillColor(WATERMARK_RED)
    pdf.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
    pdf.rotate(52)
    pdf.setFont("Helvetica-Bold", 46)
    pdf.drawCentredString(0, 20, "SPÉCIMEN – DOCUMENT FICTIF")
    pdf.drawCentredString(0, -40, "NE PAS UTILISER")
    pdf.restoreState()


def _result_box(pdf: Canvas, notice: Notice) -> None:
    """Top-right summary: how the refund is paid, or what is owed."""
    balance = notice.balance_cents
    if balance < 0:
        method = "Par dépôt direct" if notice.direct_deposit else "Par chèque"
        label = "Remboursement"
    elif balance > 0:
        method, label = "", "Solde à payer"
    else:
        method, label = "", "Solde nul"
    pdf.setFillColor(black)
    if method:
        _text(pdf, 372, 632, method, "Helvetica-Bold", 8.5)
    pdf.setStrokeColor(LIGHT_GREY)
    pdf.setLineWidth(2)
    pdf.lines([(448, 652, 460, 636), (460, 636, 448, 620)])
    _text(pdf, 470, 640, label, size=10)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(RIGHT, 624, format_money(balance))


def _draw_cover_page(pdf: Canvas, notice: Notice) -> None:
    _page_header(pdf, 1)

    # Sender (plain text, no logo) and the document control number.
    pdf.setFillColor(black)
    _text(pdf, MARGIN, 752, "Revenu Québec", "Helvetica-Bold", 13)
    _text(pdf, MARGIN, 738, notice.document_number, "Helvetica-Bold", 6.5)

    # Address block, as seen through the envelope window.
    for index, line in enumerate(
        (notice.full_name, format_address_line(notice), f"Montréal (Québec)  {notice.postal_code}")
    ):
        _text(pdf, 100, 712 - index * 12, line, "Courier", 10)

    # Identification block (top right).
    rows = (
        ("Numéro d'identification :", MASKED_SIN, "Helvetica"),
        ("Numéro de l'avis :", notice.notice_number, "Helvetica-Bold"),
        ("Date de l'avis :", format_date(notice.notice_date), "Helvetica"),
    )
    for index, (label, value, font) in enumerate(rows):
        y = 718 - index * 13
        _text(pdf, 372, y, label, font, 8.5)
        _text(pdf, 476, y, value, "Helvetica", 8.5)

    _result_box(pdf, notice)

    # Title and messages.
    pdf.setFillColor(TITLE_GREY)
    _text(pdf, 100, 568, "Avis de cotisation", "Helvetica-Bold", 22)
    pdf.setFillColor(black)
    _text(pdf, 100, 552, f"Année d'imposition {notice.tax_year}", "Helvetica-Bold", 11)

    width = RIGHT - 100
    y = _paragraph(
        pdf,
        100,
        524,
        "Merci d'avoir produit votre déclaration de revenus. Par ce geste, vous contribuez au "
        "développement économique, social et culturel du Québec.",
        width,
    )
    if notice.is_adjusted:
        message = (
            "Nous avons modifié votre déclaration de revenus. Les changements sont expliqués "
            "à la page 2."
        )
    else:
        message = "Nous avons accepté votre déclaration de revenus telle que soumise."
    y = _paragraph(pdf, 100, y, message, width, "Helvetica-Bold")
    y = _paragraph(
        pdf,
        100,
        y,
        "Vous trouverez le détail des calculs ainsi que les renseignements relatifs à votre "
        "avis de cotisation à la page suivante.",
        width,
    )
    y = _paragraph(
        pdf,
        100,
        y,
        "Conservez précieusement cet avis. Il contient des renseignements qui vous permettront "
        "de vous identifier si vous avez à communiquer avec nous ou si vous souhaitez vous "
        "inscrire à Mon dossier pour les citoyens.",
        width,
    )
    if notice.balance_cents < 0 and notice.direct_deposit:
        important = (
            "IMPORTANT : Nous déposerons votre remboursement dans votre compte bancaire. Si "
            "nous ne pouvons pas déposer ce remboursement, nous vous enverrons un chèque."
        )
    elif notice.balance_cents < 0:
        important = "IMPORTANT : Nous vous enverrons votre remboursement par chèque."
    elif notice.balance_cents > 0:
        important = (
            "IMPORTANT : Payez le solde dès que possible pour éviter que des intérêts "
            "s'ajoutent au montant que vous devez."
        )
    else:
        important = ""
    if important:
        _paragraph(pdf, 100, y, important, width, "Helvetica-Bold")

    _text(pdf, 100, 150, "MON DOSSIER POUR LES CITOYENS", "Helvetica-Bold", 9)
    _text(pdf, 330, 150, "> revenuquebec.ca/mondossier", size=8)
    _page_footer(pdf, notice)
    _diagonal_watermark(pdf)


def _draw_calculation_page(pdf: Canvas, notice: Notice) -> None:
    _page_header(pdf, 2)
    pdf.setFillColor(black)
    _text(pdf, MARGIN, 728, "Détail des calculs", "Helvetica-Bold", 13)

    declared_x, assessed_x, sign_x = 452, RIGHT, 372
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(MARGIN, 704, "Ligne")
    pdf.drawRightString(declared_x, 704, "Montant déclaré")
    pdf.drawRightString(assessed_x, 704, "Montant établi")

    order = [line for line in LINE_LABELS if line in notice.assessed_lines]
    order += [line for line in notice.declared_lines if line not in notice.assessed_lines]
    order.sort(key=lambda line: float(line))
    y = 688
    previous = ""
    for line in order:
        if previous in TOTAL_LINES or line == "350":
            y -= 8  # gap between groups, as on the notice
        previous = line
        bold = line in TOTAL_LINES
        font = "Helvetica-Bold" if bold else "Helvetica"
        if bold:
            pdf.setStrokeColor(LIGHT_GREY)
            pdf.setLineWidth(0.6)
            pdf.line(MARGIN + 30, y + 10, RIGHT, y + 10)
        _text(pdf, MARGIN, y, line, font, 9)
        _text(pdf, MARGIN + 34, y, LINE_LABELS[line], font, 9)
        _text(pdf, sign_x, y, LINE_SIGNS[line], size=9)
        pdf.setFont(font, 9)
        pdf.drawRightString(declared_x, y, format_amount(notice.declared_lines.get(line, 0)))
        pdf.drawRightString(assessed_x, y, format_amount(notice.assessed_lines.get(line, 0)))
        y -= 14

    if notice.is_adjusted:
        changed = next(
            line
            for line in INCOME_LINES
            if notice.declared_lines.get(line, 0) != notice.assessed_lines.get(line, 0)
        )
        added = notice.assessed_lines.get(changed, 0) - notice.declared_lines.get(changed, 0)
        y -= 14
        _text(pdf, MARGIN, y, "Explication des changements", "Helvetica-Bold", 10)
        _paragraph(
            pdf,
            MARGIN,
            y - 16,
            f"Ligne {changed} : nous avons ajouté {format_money(added)} à vos "
            f"{LINE_LABELS[changed].lower()}, selon les relevés que nous avons reçus. Les "
            "montants des lignes qui en dépendent ont été recalculés.",
            RIGHT - MARGIN,
        )

    _page_footer(pdf, notice)
    _diagonal_watermark(pdf)


def render_pdf(notice: Notice) -> bytes:
    """Two-page notice. invariant=True keeps the bytes identical between runs."""
    buffer = io.BytesIO()
    pdf = Canvas(buffer, pagesize=LETTER, invariant=True)
    pdf.setTitle(f"Avis de cotisation {notice.tax_year} – {WATERMARK}")
    pdf.setAuthor("Iris mock notice generator")
    _draw_cover_page(pdf, notice)
    pdf.showPage()
    _draw_calculation_page(pdf, notice)
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
