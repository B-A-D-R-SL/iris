# AI contribution: 50% or more AI-generated
"""Two-page PDF layout of a notice (reportlab).

The layout follows a redacted sample notice (tax year 2018) published as an
example: a cover page, then "Détail des calculs" with the declared and the
assessed amount of every TP-1 line. Every page carries the SPECIMEN watermark.
"""

from __future__ import annotations

import datetime as dt
import io

from reportlab.lib.colors import Color, HexColor, black
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

from notices import Notice
from tax import DEDUCTION_LINES, INCOME_LINES, LINE_LABELS

WATERMARK = "SPÉCIMEN – DOCUMENT FICTIF – NE PAS UTILISER"
MASKED_SIN = "XXX XXX XXX"
FORM_CODE = "TPF-99 (SPÉCIMEN)"
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

# Lines printed in bold with a rule above them.
TOTAL_LINES = frozenset({"199", "275", "299", "399", "432", "450", "465", "478", "479"})
# Sign printed next to each line, as on the notice.
LINE_SIGNS = {"199": "=", "275": "=", "299": "=", "377": "=", "377.1": "=", "399": "="}
LINE_SIGNS |= {"401": "=", "406": "-", "432": "=", "450": "=", "465": "=", "478": "=", "479": "="}
LINE_SIGNS |= {line: "+" for line in INCOME_LINES} | {line: "-" for line in DEDUCTION_LINES}
LINE_SIGNS |= {"295": "-", "297": "-", "350": "", "451": "", "456": "+", "462": "+"}

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
