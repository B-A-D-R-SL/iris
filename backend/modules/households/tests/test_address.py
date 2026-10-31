# AI contribution: 50% or more AI-generated
"""Pure/table-driven domain tests; no database required."""

from datetime import date

import pytest

from modules.households.domain.address import normalize_address, normalize_postal_code
from modules.households.domain.person import normalize_person, validate_birth_date


@pytest.mark.parametrize(
    ("number", "street", "unit", "code", "key"),
    [
        ("123", "rue Saint-Denis", "4", "h2x1y4", "123|R SAINT-DENIS|4|H2X1Y4"),
        ("123", " R  Saint-Denis ", "4", "H2X 1Y4", "123|R SAINT-DENIS|4|H2X1Y4"),
        ("45B", "avenue Émile", "", "H3A 0A1", "45B|AV EMILE||H3A0A1"),
        (
            "10",
            "Boulevard René-Lévesque",
            None,
            "h3b 2c4",
            "10|BD RENE-LEVESQUE||H3B2C4",
        ),
        ("9", "chemin des Pins", "2B", "H2W 1R3", "9|CH DES PINS|2B|H2W1R3"),
        ("9", "rueil", "2B", "H2W1R3", "9|RUEIL|2B|H2W1R3"),
    ],
)
def test_address_normalizes_equivalent_spellings(number, street, unit, code, key):
    assert normalize_address(number, street, unit, code) == key


@pytest.mark.parametrize(
    "code", ["", "123 456", "H2X 1", "H2X?1Y4", "H2X 1Y40", "D2X 1Y4"]
)
def test_reject_invalid_postal_codes(code):
    with pytest.raises(ValueError):
        normalize_postal_code(code)


def test_name_key_removes_accents_without_merging_birthdates():
    assert (
        normalize_person("Émilie", "D'Arc", date(1998, 3, 12))
        == "D'ARC|EMILIE|1998-03-12"
    )
    assert normalize_person("Émilie", "D'Arc", date(1998, 3, 12)) != normalize_person(
        "Émilie", "D'Arc", date(1999, 3, 12)
    )


@pytest.mark.parametrize(
    "dob,valid", [(date(2008, 10, 31), True), (date(2008, 11, 1), False)]
)
def test_holder_age_boundary(dob, valid):
    if valid:
        validate_birth_date(dob, date(2026, 10, 31), holder=True)
    else:
        with pytest.raises(ValueError):
            validate_birth_date(dob, date(2026, 10, 31), holder=True)
