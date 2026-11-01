# AI contribution: 50% or more AI-generated
"""Django admin login using the same password-attempt limit as Iris sign-in."""

from typing import Any

from allauth.account.adapter import get_adapter
from django.contrib.admin.forms import AdminAuthenticationForm
from django.views.decorators.debug import sensitive_variables


class RateLimitedAdminAuthenticationForm(AdminAuthenticationForm):
    """Apply the allauth account adapter's shared lockout to admin sign-in."""

    @sensitive_variables()
    def clean(self) -> dict[str, Any]:
        """Authenticate once through the rate-limited adapter."""
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if email is not None and password:
            self.user_cache = get_adapter().authenticate(
                self.request, email=email, password=password
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data
