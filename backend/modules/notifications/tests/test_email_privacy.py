# AI contribution: 50% or more AI-generated
"""US-59: guard the bilingual notification catalog against sensitive fields."""

from pathlib import Path

import pytest
from django.template import Context, Engine
from django.test import override_settings

from modules.notifications.rendering import TEMPLATE_KEYS, render, validate_context

ORIGIN = "https://iris.example.test"
SENSITIVE_FIELDS = ("income", "score", "tier", "notice_value", "date_of_birth")
MARKERS = {field: f"PRIVATE_{field.upper()}_VALUE" for field in SENSITIVE_FIELDS}
ACTION_CONTEXT = {
    "account_confirmation": {"confirmation_url": f"{ORIGIN}/confirm/token"},
    "password_reset": {"reset_url": f"{ORIGIN}/reset/token"},
    "invitation": {"invitation_url": f"{ORIGIN}/invitation/{'A' * 43}"},
    "walk_in_set_password": {"invitation_url": f"{ORIGIN}/invitation/{'A' * 43}"},
    "partner_application_approved": {
        "invitation_url": f"{ORIGIN}/invitation/{'A' * 43}"
    },
    "partner_application_received": {"business_name": "Example shop"},
    "partner_application_rejected": {"reason": "Outside the service area"},
    "household_suspended": {"reason": "Review required"},
    "household_reactivated": {"reason": "Review completed"},
    "reservation_cancelled_by_store": {
        "store_name": "Example shop",
        "listing_title": "Bread",
        "quantity": "2",
    },
}
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates" / "notifications"


def test_all_notification_templates_are_in_the_reviewed_catalog() -> None:
    actual = {
        path.relative_to(TEMPLATE_DIR).as_posix()
        for path in TEMPLATE_DIR.rglob("*")
        if path.is_file()
    }
    expected = {"message.html"} | {
        f"{language}/{key}_{part}.txt"
        for language in ("en", "fr")
        for key in TEMPLATE_KEYS
        for part in ("subject", "body")
    }
    assert actual == expected


@pytest.mark.parametrize(
    "path", sorted(TEMPLATE_DIR.rglob("*.txt")) + [TEMPLATE_DIR / "message.html"]
)
def test_templates_do_not_render_sensitive_fields(path: Path) -> None:
    # Render directly with poison values so even a newly added template variable
    # fails this test, rather than disappearing as an undefined Django variable.
    context = {
        **MARKERS,
        "language": "en",
        "body": "Body",
        "subject": "Subject",
        "action_url": ORIGIN,
    }
    output = (
        Engine().from_string(path.read_text(encoding="utf-8")).render(Context(context))
    )
    for marker in MARKERS.values():
        assert marker not in output


@pytest.mark.parametrize("key", sorted(TEMPLATE_KEYS))
@pytest.mark.parametrize("field", SENSITIVE_FIELDS)
@override_settings(PUBLIC_APP_ORIGIN=ORIGIN)
def test_sensitive_context_is_rejected_for_every_template(key: str, field: str) -> None:
    context = {**ACTION_CONTEXT.get(key, {}), field: MARKERS[field]}
    with pytest.raises(ValueError, match="^Invalid email context fields$") as error:
        validate_context(key, context)
    assert MARKERS[field] not in str(error.value)


@pytest.mark.parametrize("key", sorted(TEMPLATE_KEYS - ACTION_CONTEXT.keys()))
@pytest.mark.parametrize(
    "language, instruction", [("en", "Sign in"), ("fr", "Connectez-vous")]
)
@override_settings(PUBLIC_APP_ORIGIN=ORIGIN)
def test_account_notices_direct_recipients_to_sign_in(
    key: str, language: str, instruction: str
) -> None:
    message = render(key, language, {})
    assert instruction in message.text
    assert instruction in message.html
    assert f"{ORIGIN}/sign-in" in message.text
    assert f'href="{ORIGIN}/sign-in"' in message.html


@pytest.mark.parametrize(
    "key",
    ["household_suspended", "household_reactivated", "reservation_cancelled_by_store"],
)
@pytest.mark.parametrize(
    "language, instruction", [("en", "Sign in"), ("fr", "Connectez-vous")]
)
@override_settings(PUBLIC_APP_ORIGIN=ORIGIN)
def test_account_notices_with_reviewed_context_direct_to_sign_in(
    key: str, language: str, instruction: str
) -> None:
    message = render(key, language, ACTION_CONTEXT[key])
    assert instruction in message.text and instruction in message.html
    assert f"{ORIGIN}/sign-in" in message.text
    assert f'href="{ORIGIN}/sign-in"' in message.html
