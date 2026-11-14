# AI contribution: 50% or more AI-generated
"""ModelForm inputs normalize before model lengths are checked."""

from collections.abc import Callable
from typing import Any

from django import forms
from django.core.exceptions import ValidationError


class ContactField(forms.CharField):
    """Keep formatted raw input intact until its shared normalizer validates it."""

    def __init__(
        self, *, normalize: Callable[[str], str], message: Any, **kwargs: Any
    ) -> None:
        self.normalize = normalize
        self.message = message
        # No raw maxlength: canonical lengths are checked by the model afterwards.
        super().__init__(**kwargs)

    def to_python(self, value: Any) -> str:
        value = super().to_python(value)
        if not value:
            return value
        try:
            return self.normalize(value)
        except ValueError as exc:
            raise ValidationError(self.message, code="invalid") from exc
