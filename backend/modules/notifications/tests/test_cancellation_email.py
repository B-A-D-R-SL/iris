# AI contribution: 50% or more AI-generated
"""The store cancellation email names what was cancelled (US-14)."""

from collections.abc import Iterator

import pytest
from django.test import override_settings

from modules.notifications.rendering import render, validate_context

KEY = "reservation_cancelled_by_store"
CONTEXT = {
    "store_name": "Épicerie Démo du Quartier",
    "listing_title": "Bread bundle",
    "quantity": "3",
}


@pytest.fixture(autouse=True)
def _public_origin() -> Iterator[None]:
    with override_settings(PUBLIC_APP_ORIGIN="https://iris.example.test"):
        yield


# rule: BR-STORE-003
def test_english_body_names_quantity_listing_and_store() -> None:
    message = render(KEY, "en", CONTEXT)

    assert (
        "Your reservation for 3 × Bread bundle at Épicerie Démo du Quartier "
        "has been cancelled because the store can no longer offer this pickup."
    ) in message.text
    assert "This was not caused by you and does not count against you." in message.text


# rule: BR-STORE-003
def test_french_body_names_quantity_listing_and_store() -> None:
    message = render(KEY, "fr", CONTEXT)

    assert (
        "Votre réservation de 3 × Bread bundle chez Épicerie Démo du Quartier "
        "a été annulée"
    ) in message.text
    assert "Vous n’y êtes pour rien et cela ne compte pas contre vous." in message.text


def test_names_are_escaped_in_html() -> None:
    message = render(KEY, "en", {**CONTEXT, "listing_title": "<b>Bread</b>"})

    assert "<b>Bread</b>" not in message.html
    assert "&lt;b&gt;Bread&lt;/b&gt;" in message.html


# rule: BR-STORE-003
@pytest.mark.parametrize(
    "change",
    [
        {"store_name": "x" * 151},
        {"listing_title": "x" * 81},
        {"listing_title": "   "},
        {"quantity": "0"},
        {"quantity": "-1"},
        {"quantity": "12345"},
        {"quantity": 3},
        {"reason": "Closed"},
    ],
)
def test_invalid_context_is_refused(change: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        validate_context(KEY, {**CONTEXT, **change})


def test_every_field_is_required() -> None:
    for missing in CONTEXT:
        context = {key: value for key, value in CONTEXT.items() if key != missing}
        with pytest.raises(ValueError):
            validate_context(KEY, context)
