# AI contribution: 50% or more AI-generated
"""Django adapters for the shared pure contact rules."""

from collections.abc import Callable, Collection, Mapping

from django.core.exceptions import ValidationError
from django.db.models import Model
from django.utils.translation import gettext_lazy as _

from modules.common.domain.contact import normalize_phone, normalize_postal_code


def validate_phone(value: str) -> None:
    try:
        normalize_phone(value)
    except ValueError as exc:
        raise ValidationError(_("Enter a Canadian telephone number.")) from exc


def validate_postal_code(value: str) -> None:
    try:
        normalize_postal_code(value)
    except ValueError as exc:
        raise ValidationError(_("Enter a Canadian postal code.")) from exc


def normalize_model_contacts(
    instance: Model,
    fields: Mapping[str, Callable[[str], str]],
    exclude: Collection[str] | None = None,
) -> None:
    """Normalize before Django checks field lengths; leave errors to validators."""
    for name, normalize in fields.items():
        value = getattr(instance, name)
        if name not in (exclude or ()) and value:
            try:
                setattr(instance, name, normalize(str(value)))
            except ValueError:
                # clean_fields should collect every field error, not stop at one.
                pass
