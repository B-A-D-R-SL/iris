# AI contribution: 50% or more AI-generated
"""Public allauth recovery: the emailed key authorizes only its active owner."""

from typing import Any

from allauth.account.adapter import get_adapter
from allauth.headless.account.inputs import ResetPasswordInput, ResetPasswordKeyInput
from allauth.headless.account.response import PasswordResetKeyResponse
from allauth.headless.account.views import ResetPasswordView
from allauth.headless.internal.restkit.response import ErrorResponse
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _

from modules.accounts.models import User


class StringPasswordField(forms.CharField):
    def to_python(self, value: Any) -> str | None:
        """JSON containers must never become a password through string coercion."""
        if not isinstance(value, str):
            raise ValidationError(_("Enter a valid value."), code="invalid")
        return super().to_python(value)


class ActiveResetPasswordInput(ResetPasswordInput):
    password = StringPasswordField()

    def _clean_key_link(self) -> str:
        """A deactivated account cannot use a link issued before deactivation."""
        key = super()._clean_key_link()
        if not self.user.is_active:
            raise get_adapter().validation_error("invalid_password_reset")
        return key


class SingleUseResetPasswordView(ResetPasswordView):
    # Public by design: every role and anonymous callers need the target's key.
    # Session identity grants no authority to change somebody else's password.
    input_class = ActiveResetPasswordInput
    input: ActiveResetPasswordInput

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Key lookup follows the same active-account restriction as submission."""
        key_input = ResetPasswordKeyInput(
            data={"key": request.headers.get("X-Password-Reset-Key", "")}
        )
        if key_input.is_valid() and not key_input.user.is_active:
            key_input.add_error(
                "key", get_adapter().validation_error("invalid_password_reset")
            )
        if key_input.errors:
            return ErrorResponse(request, input=key_input)
        return PasswordResetKeyResponse(request, key_input.user)

    @transaction.atomic
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Keep token validation and password replacement in the same row lock."""
        # The upstream rate limiter runs before this transaction. Including its
        # database-cache writes in the user lock can deadlock unrelated requests.
        User.objects.select_for_update().get(pk=self.input.user.pk)
        self.input = self.input_class(data=self.data)
        if not self.input.is_valid():
            return self.handle_invalid_input(self.input)
        return super().post(request, *args, **kwargs)
