# AI contribution: 50% or more AI-generated
"""Bilingual content, restricted context, and trusted link regression tests."""

from collections.abc import Iterator

import pytest
from django.test import override_settings
from django.utils import translation

from modules.notifications.rendering import TEMPLATE_KEYS, render, validate_context

ORIGIN = "https://iris.example.test"
INVITATION_URL = f"{ORIGIN}/invitation/{'A' * 43}"
EXPECTED_KEYS = {
    "account_confirmation",
    "password_reset",
    "invitation",
    "walk_in_set_password",
    "partner_application_received",
    "partner_application_approved",
    "partner_application_rejected",
    "file_approved",
    "file_in_review",
    "file_invited_in_person",
    "file_rejected",
    "expiry_reminder",
    "reservation_confirmed",
    "pickup_window_open",
    "reservation_cancelled_by_store",
    "strike",
    "digest",
    "need_match",
    "household_suspended",
    "household_reactivated",
}
LINK_CONTEXTS = [
    ("account_confirmation", "confirmation_url", f"{ORIGIN}/confirm/token"),
    ("password_reset", "reset_url", f"{ORIGIN}/reset/token"),
    ("invitation", "invitation_url", INVITATION_URL),
    ("walk_in_set_password", "invitation_url", INVITATION_URL),
    ("partner_application_approved", "invitation_url", INVITATION_URL),
]


@pytest.fixture(autouse=True)
def _public_origin() -> Iterator[None]:
    with override_settings(PUBLIC_APP_ORIGIN=ORIGIN):
        yield


def _context(template_key: str) -> dict[str, str]:
    if template_key == "partner_application_received":
        return {"business_name": "Commerce Exemple"}
    if template_key in {
        "partner_application_rejected",
        "household_suspended",
        "household_reactivated",
    }:
        return {"reason": "Outside our current service area"}
    for key, field, url in LINK_CONTEXTS:
        if key == template_key:
            return {field: url}
    return {}


def test_catalog_covers_every_requested_and_existing_notice() -> None:
    assert TEMPLATE_KEYS == EXPECTED_KEYS


# rule: BR-NOTIF-003
@pytest.mark.parametrize("key", sorted(EXPECTED_KEYS))
@pytest.mark.parametrize("language", ["fr", "en"])
def test_every_template_has_subject_text_and_html(key: str, language: str) -> None:
    """Every required family is deliverable with independently selected locale."""
    message = render(key, language, _context(key))
    other_language = "en" if language == "fr" else "fr"
    other = render(key, other_language, _context(key))
    assert message.subject and message.subject != other.subject
    assert message.text and message.text != other.text
    assert f'<html lang="{language}">' in message.html
    assert message.subject in message.html
    assert f'href="{ORIGIN}/' in message.html
    assert "{{" not in message.text + message.html
    assert "{%" not in message.text + message.html
    assert "AI contribution" not in message.subject + message.text + message.html
    assert "\n" not in message.subject and "\r" not in message.subject


# rule: BR-NOTIF-003
def test_recipient_locale_overrides_worker_translation_state() -> None:
    with translation.override("fr"):
        english = render("password_reset", "en", {"reset_url": f"{ORIGIN}/reset"})
    with translation.override("en"):
        french = render("password_reset", "fr", {"reset_url": f"{ORIGIN}/reset"})
    assert english.subject == "Reset your Iris password"
    assert french.subject == "Réinitialisez votre mot de passe Iris"


# rule: BR-NOTIF-003
def test_business_name_is_plain_text_and_escaped_in_html() -> None:
    name = 'Commerce <script>alert("x")</script> & associés'
    message = render("partner_application_received", "fr", {"business_name": name})
    assert name in message.text
    assert "<script>" not in message.html
    assert "&lt;script&gt;" in message.html
    assert "&amp; associés" in message.html
    assert "&amp;lt;script&amp;gt;" not in message.html
    assert name not in message.subject


# rule: BR-NOTIF-003
@pytest.mark.parametrize("language", ["fr", "en"])
def test_partner_rejection_includes_its_bounded_reason_and_escapes_html(
    language: str,
) -> None:
    reason = 'Service area <script>alert("x")</script> & capacity'
    message = render("partner_application_rejected", language, {"reason": reason})
    assert reason in message.text
    assert "<script>" not in message.html
    assert "&lt;script&gt;" in message.html
    assert "&amp; capacity" in message.html
    assert "&amp;lt;script&amp;gt;" not in message.html
    assert reason not in message.subject


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "reason", [None, 12, "", "  ", "x" * 501, "bad\x00reason", "bad\ud800reason"]
)
def test_partner_rejection_reason_must_match_the_existing_field_contract(
    reason: object,
) -> None:
    with pytest.raises(ValueError, match="Invalid email context value"):
        validate_context("partner_application_rejected", {"reason": reason})


# rule: BR-NOTIF-003
def test_partner_rejection_requires_a_reason_and_retains_the_500_character_bound() -> (
    None
):
    with pytest.raises(ValueError, match="Invalid email context fields"):
        validate_context("partner_application_rejected", {})
    assert validate_context(
        "partner_application_rejected", {"reason": "  " + "x" * 500 + "  "}
    ) == {"reason": "x" * 500}


# rule: BR-NOTIF-003
@pytest.mark.parametrize("key", ["household_suspended", "household_reactivated"])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_household_status_includes_its_validated_reason_and_escapes_html_once(
    key: str, language: str
) -> None:
    reason = 'Review <script>alert("x")</script> & safety'
    message = render(key, language, {"reason": reason})
    assert reason in message.text
    assert "<script>" not in message.html
    assert "&lt;script&gt;" in message.html
    assert "&amp; safety" in message.html
    assert "&amp;lt;script&amp;gt;" not in message.html
    assert reason not in message.subject
    assert ("Motif :" if language == "fr" else "Reason:") in message.text


# rule: BR-NOTIF-003
@pytest.mark.parametrize("key", ["household_suspended", "household_reactivated"])
def test_household_status_requires_a_reason_with_the_schema_absolute_bound(
    key: str,
) -> None:
    with pytest.raises(ValueError, match="Invalid email context fields"):
        validate_context(key, {})
    reason = "x" * 2000
    assert validate_context(key, {"reason": f"  {reason}  "}) == {"reason": reason}
    assert reason in render(key, "en", {"reason": reason}).text


# rule: BR-NOTIF-003
@pytest.mark.parametrize("key", ["household_suspended", "household_reactivated"])
@pytest.mark.parametrize(
    "reason", [None, 12, "", "  ", "x" * 2001, "bad\x00reason", "bad\ud800reason"]
)
def test_household_status_refuses_invalid_reason_without_exposing_it(
    key: str, reason: object
) -> None:
    with pytest.raises(ValueError, match="^Invalid email context value$"):
        validate_context(key, {"reason": reason})


# rule: BR-NOTIF-003
@pytest.mark.parametrize("space", ["\u00a0", "\u202f", "\u2009"])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_business_name_unicode_spaces_are_normalized_only_for_display(
    space: str, language: str
) -> None:
    name = f"Boulangerie{space}Exemple"
    context = {"business_name": name}
    assert validate_context("partner_application_received", context) == {
        "business_name": name
    }
    message = render("partner_application_received", language, context)
    assert "Boulangerie Exemple" in message.text
    assert "Boulangerie Exemple" in message.html
    assert name not in message.text + message.html
    assert context["business_name"] == name


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    ("name", "display"),
    [
        ("Boulangerie\tExemple", "Boulangerie Exemple"),
        ("Boulangerie\nExemple", "Boulangerie Exemple"),
        ("Boulangerie\rExemple", "Boulangerie Exemple"),
        ("Boulangerie\u2028Exemple", "Boulangerie Exemple"),
        ("Boulangerie\u2029Exemple", "Boulangerie Exemple"),
        ("Boulangerie\u200bExemple", "BoulangerieExemple"),
        ("Boulangerie\u200dExemple", "BoulangerieExemple"),
        ("Boulangerie\x01Exemple", "BoulangerieExemple"),
    ],
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_business_name_controls_are_removed_from_the_display_copy(
    name: str, display: str, language: str
) -> None:
    context = {"business_name": name}
    assert validate_context("partner_application_received", context) == context
    message = render("partner_application_received", language, context)
    assert display in message.text
    assert display in message.html
    assert name not in message.text + message.html
    assert context["business_name"] == name


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    ("language", "receipt"),
    [
        ("fr", "Nous avons bien reçu votre demande."),
        ("en", "We received your application."),
    ],
)
def test_invisible_business_name_uses_a_generic_receipt(
    language: str, receipt: str
) -> None:
    context = {"business_name": "\u200d\u200d"}
    assert validate_context("partner_application_received", context) == context
    message = render("partner_application_received", language, context)
    assert receipt in message.text
    assert receipt in message.html
    assert "\u200d" not in message.text + message.html
    assert "for ." not in message.text
    assert "pour ." not in message.text


# rule: BR-NOTIF-003
def test_action_link_query_is_escaped_in_html() -> None:
    url = f"{ORIGIN}/reset?token=example&step=choose"
    message = render("password_reset", "en", {"reset_url": url})
    assert url in message.text
    assert 'href="https://iris.example.test/reset?token=example&amp;step=choose"' in (
        message.html
    )


# rule: BR-NOTIF-003
def test_validation_copies_context_and_removes_reserved_language() -> None:
    context = {"business_name": "Commerce Exemple", "language": "en"}
    copied = validate_context("partner_application_received", context)
    context["business_name"] = "Changed after queueing"
    assert copied == {"business_name": "Commerce Exemple"}
    assert context["language"] == "en"


# rule: BR-NOTIF-003
@pytest.mark.parametrize("key,field,url", LINK_CONTEXTS)
def test_security_templates_require_their_specific_link(
    key: str, field: str, url: str
) -> None:
    with pytest.raises(ValueError, match="Invalid email context fields"):
        validate_context(key, {})
    assert validate_context(key, {field: url}) == {field: url}


# rule: BR-NOTIF-003
def test_partner_receipt_requires_the_business_name() -> None:
    with pytest.raises(ValueError, match="Invalid email context fields"):
        validate_context("partner_application_received", {})


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "field", ["reason", "notes", "income", "email", "token", "body", "user"]
)
def test_unreviewed_or_sensitive_context_fields_are_refused(field: str) -> None:
    private_value = "PRIVATE_VALUE_SHOULD_NEVER_APPEAR"
    with pytest.raises(ValueError) as error:
        validate_context("file_rejected", {field: private_value})
    assert private_value not in str(error.value)
    assert str(error.value) == "Invalid email context fields"


# rule: BR-NOTIF-003
def test_security_link_cannot_be_added_to_an_unrelated_template() -> None:
    with pytest.raises(ValueError, match="Invalid email context fields"):
        validate_context("digest", {"reset_url": f"{ORIGIN}/reset"})


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "value",
    [
        None,
        12,
        [],
        {},
        "",
        "  ",
        "x\x00y",
        "x\ud800y",
        "x" * 151,
    ],
)
def test_invalid_business_names_are_refused(value: object) -> None:
    with pytest.raises(ValueError, match="Invalid email context value"):
        validate_context("partner_application_received", {"business_name": value})


# rule: BR-NOTIF-003
@pytest.mark.parametrize("value", [None, 12, [], {}, "", "es"])
def test_invalid_reserved_language_is_refused(value: object) -> None:
    with pytest.raises(ValueError, match="Invalid email language"):
        validate_context("digest", {"language": value})


# rule: BR-NOTIF-003
@pytest.mark.parametrize("language", ["", "es", None, []])
def test_render_requires_a_supported_explicit_language(language: object) -> None:
    with pytest.raises(ValueError, match="Invalid email language"):
        render("digest", language, {})  # type: ignore[arg-type]


# rule: BR-NOTIF-003
@pytest.mark.parametrize("key", ["../digest", "missing", "", None, []])
def test_unknown_template_is_refused_without_path_resolution(key: object) -> None:
    with pytest.raises(ValueError, match="Unknown email template"):
        validate_context(key, {})  # type: ignore[arg-type]


# rule: BR-NOTIF-003
def test_non_mapping_context_is_refused() -> None:
    with pytest.raises(ValueError, match="Invalid email context"):
        validate_context("digest", ["unexpected"])  # type: ignore[arg-type]


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "url",
    [
        "https://other.example.test/reset",
        "https://iris.example.test.other.test/reset",
        "https://iris.example.test:444/reset",
        "http://iris.example.test/reset",
        "//iris.example.test/reset",
        "javascript:alert(1)",
        "https://user@iris.example.test/reset",
        "https://user:password@iris.example.test/reset",
        "https://iris.example.test:invalid/reset",
        "https://iris.example.test:65536/reset",
        "https://iris.example.test:0/reset",
        "https://iris.example.test\\@other.test/reset",
        "https://iris.example.test/reset\nprivate",
        "https://iris.example.test/reset private",
        "https://[invalid/reset",
        f"{ORIGIN}/" + "a" * 2048,
    ],
)
def test_untrusted_or_malformed_action_links_are_refused(url: str) -> None:
    with pytest.raises(ValueError) as error:
        validate_context("password_reset", {"reset_url": url})
    assert url not in str(error.value)


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "suffix", ["", "short", "A" * 43 + "/", "A" * 43 + "?next=1", "A" * 43 + "#x"]
)
def test_invitation_links_use_the_existing_route_and_token_shape(suffix: str) -> None:
    with pytest.raises(ValueError, match="Invalid email invitation link"):
        validate_context(
            "invitation", {"invitation_url": f"{ORIGIN}/invitation/{suffix}"}
        )


# rule: BR-NOTIF-003
def test_default_https_port_is_the_same_origin() -> None:
    url = "https://iris.example.test:443/reset"
    assert validate_context("password_reset", {"reset_url": url}) == {"reset_url": url}


# rule: BR-NOTIF-003
@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_configured_loopback_http_works_with_debug_disabled(host: str) -> None:
    origin = f"http://{host}:5173"
    with override_settings(PUBLIC_APP_ORIGIN=origin, DEBUG=False):
        message = render("digest", "en", {})
    assert f"{origin}/sign-in" in message.text


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "origin",
    [
        "",
        None,
        "http://iris.example.test",
        f"{ORIGIN}/prefix",
        f"{ORIGIN}?x=1",
        f"{ORIGIN}#x",
    ],
)
def test_invalid_public_origin_is_refused(origin: object) -> None:
    with override_settings(PUBLIC_APP_ORIGIN=origin), pytest.raises(ValueError):
        render("digest", "en", {})


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "key", ["partner_application_received", "partner_application_rejected"]
)
def test_partner_contacts_without_accounts_use_the_public_landing_page(
    key: str,
) -> None:
    message = render(key, "en", _context(key))
    assert message.text.endswith(f"{ORIGIN}/\n")
    assert "/sign-in" not in message.text


# rule: BR-NOTIF-003
def test_generic_status_link_can_be_overridden_with_a_trusted_page() -> None:
    url = f"{ORIGIN}/sign-in"
    message = render("file_approved", "en", {"sign_in_url": url})
    assert message.text.endswith(url + "\n")


# rule: BR-NOTIF-003
@pytest.mark.parametrize(
    "path",
    [
        "/sign-in?token=private",
        "/sign-in#secret",
        "/reset/private",
        f"/invitation/{'A' * 43}",
        "/household/status",
    ],
)
def test_generic_notices_cannot_carry_security_links(path: str) -> None:
    with pytest.raises(ValueError, match="Invalid email sign-in link"):
        validate_context("digest", {"sign_in_url": ORIGIN + path})
