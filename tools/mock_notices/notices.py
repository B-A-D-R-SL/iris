# AI contribution: 50% or more AI-generated
"""The people, addresses and amounts on each mock notice, and what the household declared.

Every random choice comes from Faker('fr_CA') and random.Random seeded with SEED, in a
fixed order, so the same seed gives the same notices. The cases follow
docs/04-data/mock-notices-of-assessment.md.
"""

from __future__ import annotations

import datetime as dt
import random
import string
import unicodedata
from dataclasses import dataclass, replace

from faker import Faker

from tax import calculations

SEED = 42
CURRENT_TAX_YEAR = 2025
OLD_TAX_YEAR = 2023

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
# Notices where Revenu Québec changed the return: an income the person did not
# declare was added, so "Montant déclaré" and "Montant établi" differ.
ADJUSTED_NUMBERS = (3, 11, 17, 24, 29, 34, 41)

# Clean files whose declared name differs in a way the name check must tolerate
# (business rules: case and accents ignored, extra middle names allowed).
MIDDLE_NAME_NUMBERS = (5, 20)
UPPERCASE_NUMBERS = (8, 25)
ACCENT_CONTROLS = 2


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
    declared_lines, assessed_lines = calculations(
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
