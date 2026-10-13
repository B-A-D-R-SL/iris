# AI contribution: 50% or more AI-generated
"""The two columns of 'Détail des calculs': every TP-1 line as declared and as assessed.

Simplified Québec income tax, amounts in cents. Line labels come from the 2025 TP-1.
"""

from __future__ import annotations

import random

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

# Simplified Québec tax: basic personal amount, 14 % credit, brackets (cents).
TAX_RULES = {
    2025: {"basic": 18_571_00, "brackets": ((53_255_00, 0.14), (106_495_00, 0.19))},
    2023: {"basic": 17_183_00, "brackets": ((49_275_00, 0.14), (98_540_00, 0.19))},
}
TOP_RATE = 0.24


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


def calculations(
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
