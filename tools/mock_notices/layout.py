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


# Cover page text, word for word from the sample notice.
THANKS = (
    "Merci d'avoir produit votre déclaration de revenus. Par ce geste, vous contribuez au "
    "développement économique, social et culturel du Québec."
)
ACCEPTED = "Nous avons accepté votre déclaration de revenus telle que soumise."
ADJUSTED = (
    "Nous avons modifié votre déclaration de revenus. Les changements sont expliqués à la page 2."
)
DETAILS = (
    "Vous trouverez le détail des calculs ainsi que les renseignements relatifs à votre "
    "avis de cotisation à la page suivante."
)
KEEP_NOTICE = (
    "Conservez précieusement cet avis. Il contient des renseignements qui vous permettront "
    "de vous identifier si vous avez à communiquer avec nous ou si vous souhaitez vous "
    "inscrire à Mon dossier pour les citoyens."
)
REFUND_BY_DEPOSIT = (
    "IMPORTANT : Nous déposerons votre remboursement dans votre compte bancaire. Si "
    "nous ne pouvons pas déposer ce remboursement, nous vous enverrons un chèque."
)
REFUND_BY_CHEQUE = "IMPORTANT : Nous vous enverrons votre remboursement par chèque."
BALANCE_OWED = (
    "IMPORTANT : Payez le solde dès que possible pour éviter que des intérêts "
    "s'ajoutent au montant que vous devez."
)

# Calculation table columns.
SIGN_X, DECLARED_X, ASSESSED_X = 372, 452, RIGHT


def review_message(notice: Notice) -> str:
    """Cover page: whether Revenu Québec accepted the return or changed it."""
    return ADJUSTED if notice.is_adjusted else ACCEPTED


def important_message(notice: Notice) -> str:
    """Cover page: how the refund is paid or that a balance is owed; empty at zero."""
    if notice.balance_cents < 0:
        return REFUND_BY_DEPOSIT if notice.direct_deposit else REFUND_BY_CHEQUE
    return BALANCE_OWED if notice.balance_cents > 0 else ""


def calculation_order(notice: Notice) -> list[str]:
    """Page 2 rows: the assessed TP-1 lines and any line only declared, in number order."""
    order = [line for line in LINE_LABELS if line in notice.assessed_lines]
    order += [line for line in notice.declared_lines if line not in notice.assessed_lines]
    return sorted(order, key=float)


def change_explanation(notice: Notice) -> str:
    """Page 2 note on an adjusted notice, about the first income line that changed."""
    declared, assessed = notice.declared_lines, notice.assessed_lines
    changed = next(line for line in INCOME_LINES if declared.get(line, 0) != assessed.get(line, 0))
    added = assessed.get(changed, 0) - declared.get(changed, 0)
    return (
        f"Ligne {changed} : nous avons ajouté {format_money(added)} à vos "
        f"{LINE_LABELS[changed].lower()}, selon les relevés que nous avons reçus. Les "
        "montants des lignes qui en dépendent ont été recalculés."
    )


def _sender(pdf: Canvas, notice: Notice) -> None:
    """Sender (plain text, no logo) and the document control number."""
    pdf.setFillColor(black)
    _text(pdf, MARGIN, 752, "Revenu Québec", "Helvetica-Bold", 13)
    _text(pdf, MARGIN, 738, notice.document_number, "Helvetica-Bold", 6.5)


def _address_block(pdf: Canvas, notice: Notice) -> None:
    """Name and address, as seen through the envelope window."""
    city = f"Montréal (Québec)  {notice.postal_code}"
    for index, line in enumerate((notice.full_name, format_address_line(notice), city)):
        _text(pdf, 100, 712 - index * 12, line, "Courier", 10)


def _identification_block(pdf: Canvas, notice: Notice) -> None:
    """Top right: masked SIN, notice number and notice date."""
    rows = (
        ("Numéro d'identification :", MASKED_SIN, "Helvetica"),
        ("Numéro de l'avis :", notice.notice_number, "Helvetica-Bold"),
        ("Date de l'avis :", format_date(notice.notice_date), "Helvetica"),
    )
    for index, (label, value, font) in enumerate(rows):
        y = 718 - index * 13
        _text(pdf, 372, y, label, font, 8.5)
        _text(pdf, 476, y, value, "Helvetica", 8.5)


def _title(pdf: Canvas, notice: Notice) -> None:
    pdf.setFillColor(TITLE_GREY)
    _text(pdf, 100, 568, "Avis de cotisation", "Helvetica-Bold", 22)
    pdf.setFillColor(black)
    _text(pdf, 100, 552, f"Année d'imposition {notice.tax_year}", "Helvetica-Bold", 11)


def _messages(pdf: Canvas, notice: Notice) -> None:
    """Cover page paragraphs, top down; an empty IMPORTANT message is left out."""
    paragraphs = (
        (THANKS, "Helvetica"),
        (review_message(notice), "Helvetica-Bold"),
        (DETAILS, "Helvetica"),
        (KEEP_NOTICE, "Helvetica"),
        (important_message(notice), "Helvetica-Bold"),
    )
    y = 524
    for text, font in paragraphs:
        if text:
            y = _paragraph(pdf, 100, y, text, RIGHT - 100, font)


def _mon_dossier_link(pdf: Canvas) -> None:
    _text(pdf, 100, 150, "MON DOSSIER POUR LES CITOYENS", "Helvetica-Bold", 9)
    _text(pdf, 330, 150, "> revenuquebec.ca/mondossier", size=8)


def _draw_cover_page(pdf: Canvas, notice: Notice) -> None:
    _page_header(pdf, 1)
    _sender(pdf, notice)
    _address_block(pdf, notice)
    _identification_block(pdf, notice)
    _result_box(pdf, notice)
    _title(pdf, notice)
    _messages(pdf, notice)
    _mon_dossier_link(pdf)
    _page_footer(pdf, notice)
    _diagonal_watermark(pdf)


def _calculation_headings(pdf: Canvas) -> None:
    pdf.setFillColor(black)
    _text(pdf, MARGIN, 728, "Détail des calculs", "Helvetica-Bold", 13)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(MARGIN, 704, "Ligne")
    pdf.drawRightString(DECLARED_X, 704, "Montant déclaré")
    pdf.drawRightString(ASSESSED_X, 704, "Montant établi")


def _calculation_row(pdf: Canvas, notice: Notice, line: str, y: float) -> None:
    """One TP-1 line; totals are bold with a rule above them."""
    font = "Helvetica-Bold" if line in TOTAL_LINES else "Helvetica"
    if line in TOTAL_LINES:
        pdf.setStrokeColor(LIGHT_GREY)
        pdf.setLineWidth(0.6)
        pdf.line(MARGIN + 30, y + 10, RIGHT, y + 10)
    _text(pdf, MARGIN, y, line, font, 9)
    _text(pdf, MARGIN + 34, y, LINE_LABELS[line], font, 9)
    _text(pdf, SIGN_X, y, LINE_SIGNS[line], size=9)
    pdf.setFont(font, 9)
    pdf.drawRightString(DECLARED_X, y, format_amount(notice.declared_lines.get(line, 0)))
    pdf.drawRightString(ASSESSED_X, y, format_amount(notice.assessed_lines.get(line, 0)))


def _calculation_rows(pdf: Canvas, notice: Notice) -> float:
    """Draws every row from the top and returns the y just below the last one."""
    y, previous = 688, ""
    for line in calculation_order(notice):
        if previous in TOTAL_LINES or line == "350":
            y -= 8  # gap between groups, as on the notice
        _calculation_row(pdf, notice, line, y)
        previous = line
        y -= 14
    return y


def _change_explanation(pdf: Canvas, notice: Notice, y: float) -> None:
    _text(pdf, MARGIN, y, "Explication des changements", "Helvetica-Bold", 10)
    _paragraph(pdf, MARGIN, y - 16, change_explanation(notice), RIGHT - MARGIN)


def _draw_calculation_page(pdf: Canvas, notice: Notice) -> None:
    _page_header(pdf, 2)
    _calculation_headings(pdf)
    y = _calculation_rows(pdf, notice)
    if notice.is_adjusted:
        _change_explanation(pdf, notice, y - 14)
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
