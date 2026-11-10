# AI contribution: 50% or more AI-generated
"""The text and row order layout.py picks for each notice (FIX-21).

test_generate.py checks the drawn files against the committed ones; these check
each choice on its own, including balances the committed notices may not cover.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from layout import calculation_order, change_explanation, important_message, review_message
from notices import Notice, build_notices

DEPOSIT = (
    "IMPORTANT : Nous déposerons votre remboursement dans votre compte bancaire. Si nous ne "
    "pouvons pas déposer ce remboursement, nous vous enverrons un chèque."
)
CHEQUE = "IMPORTANT : Nous vous enverrons votre remboursement par chèque."
OWED = (
    "IMPORTANT : Payez le solde dès que possible pour éviter que des intérêts s'ajoutent au "
    "montant que vous devez."
)


@pytest.fixture(scope="module")
def notice() -> Notice:
    return build_notices()[0]


def _with_lines(notice: Notice, declared: dict[str, int], assessed: dict[str, int]) -> Notice:
    return replace(notice, declared_lines=declared, assessed_lines=assessed)


@pytest.mark.parametrize(
    ("refund", "owed", "direct_deposit", "expected"),
    [
        pytest.param(12_345, 0, True, DEPOSIT, id="refund-by-deposit"),
        pytest.param(1, 0, False, CHEQUE, id="smallest-refund-by-cheque"),
        pytest.param(0, 1, True, OWED, id="smallest-balance-owed-ignores-deposit"),
        pytest.param(0, 0, True, "", id="zero-balance-prints-nothing"),
    ],
)
def test_important_message_follows_the_balance_and_payment_method(
    notice: Notice, refund: int, owed: int, direct_deposit: bool, expected: str
) -> None:
    lines = {"478": refund, "479": owed}
    balance = replace(notice, assessed_lines=lines, direct_deposit=direct_deposit)

    assert important_message(balance) == expected


def test_review_message_says_the_return_was_accepted_when_nothing_changed(notice: Notice) -> None:
    accepted = _with_lines(notice, declared={"101": 100}, assessed={"101": 100})

    assert review_message(accepted) == (
        "Nous avons accepté votre déclaration de revenus telle que soumise."
    )


def test_review_message_points_to_page_2_when_an_amount_changed(notice: Notice) -> None:
    adjusted = _with_lines(notice, declared={"101": 100}, assessed={"101": 200})

    assert review_message(adjusted) == (
        "Nous avons modifié votre déclaration de revenus. Les changements sont expliqués à la "
        "page 2."
    )


def test_calculation_order_puts_a_declared_only_line_in_number_order(notice: Notice) -> None:
    lines = _with_lines(
        notice,
        declared={"101": 1, "130": 2, "199": 3},
        assessed={"377.1": 4, "101": 1, "377": 5, "199": 3},
    )

    assert calculation_order(lines) == ["101", "130", "199", "377", "377.1"]


def test_change_explanation_names_the_first_income_line_that_changed(notice: Notice) -> None:
    # 154 changed too and comes first in the dict, but 130 comes first on the TP-1;
    # 130 is missing from the declared lines, so it counts as declared at 0.
    adjusted = _with_lines(
        notice,
        declared={"154": 500, "101": 1_000},
        assessed={"154": 900, "130": 123_456, "101": 1_000},
    )

    assert change_explanation(adjusted) == (
        "Ligne 130 : nous avons ajouté 1 234,56 $ à vos intérêts et autres revenus de "
        "placement, selon les relevés que nous avons reçus. Les montants des lignes qui en "
        "dépendent ont été recalculés."
    )
