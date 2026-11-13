# AI contribution: 50% or more AI-generated
"""Reviewed bilingual templates with bounded context and trusted action links."""

import ipaddress
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

from django.conf import settings
from django.template.loader import render_to_string


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    text: str
    html: str


@dataclass(frozen=True)
class _Template:
    required: frozenset[str] = frozenset()
    action_field: str = "sign_in_url"
    default_path: str = "/sign-in"


_TEMPLATES = {
    "account_confirmation": _Template(
        frozenset({"confirmation_url"}), "confirmation_url"
    ),
    "password_reset": _Template(frozenset({"reset_url"}), "reset_url"),
    "invitation": _Template(frozenset({"invitation_url"}), "invitation_url"),
    "walk_in_set_password": _Template(frozenset({"invitation_url"}), "invitation_url"),
    "partner_application_received": _Template(
        frozenset({"business_name"}), default_path="/"
    ),
    "partner_application_approved": _Template(
        frozenset({"invitation_url"}), "invitation_url"
    ),
    "partner_application_rejected": _Template(default_path="/"),
    "file_approved": _Template(),
    "file_in_review": _Template(),
    "file_invited_in_person": _Template(),
    "file_rejected": _Template(),
    "expiry_reminder": _Template(),
    "reservation_confirmed": _Template(),
    "pickup_window_open": _Template(),
    "reservation_cancelled_by_store": _Template(),
    "strike": _Template(),
    "digest": _Template(),
    "need_match": _Template(),
    "household_suspended": _Template(),
    "household_reactivated": _Template(),
}
TEMPLATE_KEYS = frozenset(_TEMPLATES)
_INVITATION_PATH = re.compile(r"/invitation/[A-Za-z0-9_-]{43}\Z")
_INVALID_URL_CHARACTERS = re.compile(r"[\s\\\x00-\x1f\x7f]")


def _template(template_key: str) -> _Template:
    if not isinstance(template_key, str) or template_key not in _TEMPLATES:
        raise ValueError("Unknown email template")
    return _TEMPLATES[template_key]


def _url(value: str) -> SplitResult:
    if _INVALID_URL_CHARACTERS.search(value):
        raise ValueError("Invalid email action link")
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port == 0
        ):
            raise ValueError
    except ValueError:
        raise ValueError("Invalid email action link") from None
    return parsed


def _loopback(hostname: str) -> bool:
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _origin() -> SplitResult:
    value = getattr(settings, "PUBLIC_APP_ORIGIN", "")
    if not isinstance(value, str) or not value:
        raise ValueError("Email application origin is unavailable")
    origin = _url(value)
    if (
        origin.path not in {"", "/"}
        or origin.query
        or origin.fragment
        or (origin.scheme == "http" and not _loopback(origin.hostname or ""))
    ):
        raise ValueError("Invalid email application origin")
    return origin


def _origin_key(parsed: SplitResult) -> tuple[str, str, int]:
    return (
        parsed.scheme,
        parsed.hostname or "",
        parsed.port or (443 if parsed.scheme == "https" else 80),
    )


def _action_link(value: str, field: str, origin: SplitResult) -> None:
    parsed = _url(value)
    if _origin_key(parsed) != _origin_key(origin):
        raise ValueError("Email action link must use the application origin")
    if field == "invitation_url" and (
        not _INVITATION_PATH.fullmatch(parsed.path) or parsed.query or parsed.fragment
    ):
        raise ValueError("Invalid email invitation link")
    if field == "sign_in_url" and (
        parsed.path not in {"/", "/sign-in"} or parsed.query or parsed.fragment
    ):
        raise ValueError("Invalid email sign-in link")


def validate_context(
    template_key: str, context: Mapping[str, object]
) -> dict[str, str]:
    """Copy only reviewed scalar fields; errors never contain caller values.

    ``language`` is reserved for recipient resolution by the send service and is
    removed before durable queueing. Case notes, reasons, and recipient details
    are deliberately absent from every template's allowed context. Generic
    notices link only to the public landing/sign-in pages; one-use links belong
    to their dedicated account templates.
    """
    template = _template(template_key)
    if not isinstance(context, Mapping):
        # Keep one safe validation exception for the notification service.
        raise ValueError("Invalid email context")  # noqa: TRY004
    allowed = template.required | {template.action_field, "language"}
    if set(context) - allowed or not template.required <= context.keys():
        raise ValueError("Invalid email context fields")
    if "language" in context and (
        not isinstance(context["language"], str)
        or context["language"] not in {"fr", "en"}
    ):
        raise ValueError("Invalid email language")
    cleaned: dict[str, str] = {}
    origin = _origin()
    for key, value in context.items():
        if key == "language":
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Invalid email context value")
        if key == "business_name":
            # Match the existing form's name contract; sanitize its display copy
            # at render time so validation remains stable across queueing.
            if len(value) > 150 or any(
                character == "\x00" or unicodedata.category(character) == "Cs"
                for character in value
            ):
                raise ValueError("Invalid email context value")
        elif len(value) > 2048:
            raise ValueError("Invalid email context value")
        else:
            _action_link(value, key, origin)
        cleaned[key] = value
    return cleaned


def render(
    template_key: str, language: str, context: Mapping[str, object]
) -> RenderedEmail:
    """Render a captured recipient language, independent of worker locale."""
    template = _template(template_key)
    if not isinstance(language, str) or language not in {"fr", "en"}:
        raise ValueError("Invalid email language")
    cleaned = validate_context(template_key, context)
    if "business_name" in cleaned:
        name = " ".join(cleaned["business_name"].split())
        cleaned["business_name"] = "".join(
            character for character in name if character.isprintable()
        ).strip()
    action_url = cleaned.get(template.action_field)
    if action_url is None:
        action_url = _origin().geturl().rstrip("/") + template.default_path
    prefix = f"notifications/{language}/{template_key}"
    subject = render_to_string(f"{prefix}_subject.txt", cleaned).strip()
    body = render_to_string(f"{prefix}_body.txt", cleaned).strip()
    text = f"{body}\n\n{action_url}\n"
    html = render_to_string(
        "notifications/message.html",
        {
            "subject": subject,
            "body": body,
            "action_url": action_url,
            "language": language,
        },
    )
    return RenderedEmail(subject=subject, text=text, html=html)
