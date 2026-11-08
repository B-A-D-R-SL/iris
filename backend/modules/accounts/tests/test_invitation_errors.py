# AI contribution: 50% or more AI-generated
"""Invitation errors expose approved translations while preserving validator codes."""

import pytest
from django.contrib.auth.password_validation import (
    MinimumLengthValidator,
    get_default_password_validators,
)
from django.core.exceptions import ValidationError
from django.utils import translation
from rest_framework.test import APIClient

from modules.accounts import services
from modules.accounts.api.views import invitation_exception_handler
from modules.accounts.models import User

URL = "/api/invitations/accept/"
PASSWORD = "error-test-invitation-657"
SECRET = "synthetic-private-error-657"


def _minimum_length():
    """Read the real configured validator instead of duplicating its policy value."""
    return next(
        validator.min_length
        for validator in get_default_password_validators()
        if isinstance(validator, MinimumLengthValidator)
    )


def _service_response(error, language):
    """Exercise the public exception handler under the request's active language."""
    with translation.override(language):
        response = invitation_exception_handler(error, {})
    assert response is not None
    assert set(response.data) == {"code", "message", "fields"}
    return response


def _assert_unused(invitation):
    """A refused input cannot consume its invitation or create the recipient."""
    invitation.refresh_from_db()
    assert invitation.accepted_at is None
    assert not User.objects.filter(email=invitation.email).exists()


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize(
    ("code", "status", "english", "french"),
    [
        (
            "invitation_invalid",
            400,
            "This invitation link is invalid.",
            "Ce lien d’invitation est invalide.",
        ),
        (
            "invitation_expired",
            400,
            "This invitation link has expired.",
            "Ce lien d’invitation a expiré.",
        ),
        (
            "invitation_used",
            400,
            "This invitation link has already been used.",
            "Ce lien d’invitation a déjà été utilisé.",
        ),
        (
            "email_already_registered",
            400,
            "An account already uses this email address.",
            "Un compte utilise déjà ce courriel.",
        ),
        (
            "invitation_unavailable",
            503,
            "Invitations are temporarily unavailable. Try again later.",
            "Les invitations sont temporairement indisponibles. Réessayez plus tard.",
        ),
    ],
)
def test_known_invitation_codes_return_only_approved_translations(
    code, status, english, french, language
):
    """Recognized codes never authorize the original exception's arbitrary text."""
    response = _service_response(ValidationError(SECRET, code=code), language)

    assert response.status_code == status
    assert response.data == {
        "code": code,
        "message": french if language == "fr" else english,
        "fields": {},
    }
    assert SECRET not in str(response.data)


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize(
    ("code", "english", "french"),
    [
        ("required", "Enter a password.", "Entrez un mot de passe."),
        (
            "password_too_short",
            "This password must contain at least {minimum} characters.",
            "Ce mot de passe doit contenir au moins {minimum} caractères.",
        ),
        (
            "password_too_similar",
            "This password is too similar to your personal information.",
            "Ce mot de passe ressemble trop à vos renseignements personnels.",
        ),
        (
            "password_too_common",
            "This password is too common.",
            "Ce mot de passe est trop courant.",
        ),
        (
            "password_entirely_numeric",
            "This password is entirely numeric.",
            "Ce mot de passe est entièrement numérique.",
        ),
    ],
)
def test_known_password_codes_return_useful_translated_feedback(
    code, english, french, language
):
    """Password feedback uses safe codes and length, never arbitrary validator text."""
    minimum = _minimum_length()
    error = ValidationError(
        {
            "password": ValidationError(
                SECRET,
                code=code,
                params={"min_length": minimum, "verbose_name": SECRET},
            )
        }
    )
    response = _service_response(error, language)

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    expected = (french if language == "fr" else english).format(minimum=minimum)
    assert response.data["fields"] == {"password": [expected]}
    assert SECRET not in str(response.data)


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("minimum", [SECRET, True])
def test_unsafe_password_length_parameters_are_not_interpolated(minimum, language):
    """Only a positive integer may appear in minimum-length guidance."""
    error = ValidationError(
        {
            "password": ValidationError(
                SECRET, code="password_too_short", params={"min_length": minimum}
            )
        }
    )
    response = _service_response(error, language)

    expected = (
        "Ce mot de passe est trop court."
        if language == "fr"
        else ("This password is too short.")
    )
    assert response.data["fields"] == {"password": [expected]}
    assert SECRET not in str(response.data)


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("kind", ["top_level", "password", "unknown_field"])
def test_unknown_service_errors_keep_exception_text_and_fields_private(
    issue_invitation, monkeypatch, caplog, language, kind
):
    """Unexpected Django validation details cannot leak through the HTTP envelope."""
    token, invitation = issue_invitation()
    private_text = f"{SECRET}:{token}:{invitation.email}:{PASSWORD}"
    leaf = ValidationError(private_text, code=SECRET)
    error = (
        leaf
        if kind == "top_level"
        else ValidationError(
            {
                "password" if kind == "password" else private_text: leaf,
            }
        )
    )

    def refuse(*args, **kwargs):
        raise error

    monkeypatch.setattr(services, "accept_invitation", refuse)
    response = APIClient().post(
        URL,
        {"token": token, "password": PASSWORD},
        format="json",
        HTTP_ACCEPT_LANGUAGE=language,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == (
        "Vérifiez les champs indiqués."
        if language == "fr"
        else "Check the highlighted fields."
    )
    expected = (
        "Entrez une valeur valide." if language == "fr" else "Enter a valid value."
    )
    field = "password" if kind == "password" else "non_field_errors"
    assert body["fields"] == ({} if kind == "top_level" else {field: [expected]})
    for value in (SECRET, token, invitation.email, PASSWORD):
        assert value not in response.content.decode()
        assert value not in caplog.text
    _assert_unused(invitation)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("required", "required"),
        ("short", "password_too_short"),
        ("common", "password_too_common"),
        ("numeric", "password_entirely_numeric"),
        ("similar", "password_too_similar"),
    ],
)
def test_service_preserves_real_validator_codes_and_safe_parameters(
    issue_invitation, kind, code
):
    """Wrapping Django password errors retains codes and params without consuming tokens."""
    token, invitation = issue_invitation()
    password = {
        "required": " " * _minimum_length(),
        "short": "short",
        "common": "password12345",
        "numeric": "9274610385721",
        "similar": invitation.email,
    }[kind]

    with pytest.raises(ValidationError) as caught:
        services.accept_invitation(token, password)

    errors = caught.value.error_dict["password"]
    matching = next(error for error in errors if error.code == code)
    if kind == "short":
        assert matching.params["min_length"] == _minimum_length()
    _assert_unused(invitation)
    assert services.accept_invitation(token, PASSWORD).email == invitation.email


@pytest.mark.django_db
@pytest.mark.parametrize("language", ["en", "fr"])
def test_real_password_rejection_has_translated_length_and_leaves_token_unused(
    issue_invitation, language
):
    """The real API preserves useful configured-length feedback without account writes."""
    token, invitation = issue_invitation()
    response = APIClient().post(
        URL,
        {"token": token, "password": "short"},
        format="json",
        HTTP_ACCEPT_LANGUAGE=language,
    )

    assert response.status_code == 400
    minimum = _minimum_length()
    expected = (
        f"Ce mot de passe doit contenir au moins {minimum} caractères."
        if language == "fr"
        else f"This password must contain at least {minimum} characters."
    )
    assert expected in response.json()["fields"]["password"]
    _assert_unused(invitation)
