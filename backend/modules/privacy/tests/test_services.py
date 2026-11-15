# AI contribution: 50% or more AI-generated
"""The shared sensitive-reason check used by household and store reasons."""

import pytest

from modules.privacy.services import household_reason_contains_sensitive_data


# rule: BR-HH-SUSPEND-004
# rule: BR-STORE-005
@pytest.mark.parametrize(
    "reason",
    [
        "Permanent resident",
        "Résident permanent",
        "Résidente permanente",
        "Statut de résidente permanente",
        "Resident permanent",
        "residente permanente",
    ],
)
def test_residency_status_is_refused_in_english_and_french(reason: str) -> None:
    assert household_reason_contains_sensitive_data(reason)


@pytest.mark.parametrize(
    "reason",
    ["Store closed for renovations", "Résidence de personnes âgées fermée"],
)
def test_ordinary_reasons_pass(reason: str) -> None:
    assert not household_reason_contains_sensitive_data(reason)
