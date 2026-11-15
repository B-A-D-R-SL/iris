# AI contribution: 50% or more AI-generated
"""FIX-14 format cases shared with Vitest, plus framework requiredness."""

import json
import re
import unicodedata
from pathlib import Path

import pytest
from rest_framework import serializers

from modules.common.api.fields import CanadianPhoneField, PostalCodeField
from modules.common.domain.contact import (
    InvalidPhone,
    InvalidPostalCode,
    normalize_phone,
    normalize_postal_code,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_CASES = json.loads(
    (_PROJECT_ROOT / "mock-data/validation/contact-values.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("kind", ["phone", "postal"])
def test_shared_cases_define_normalization_and_rejection(kind):
    normalize = {"phone": normalize_phone, "postal": normalize_postal_code}[kind]
    field = {"phone": CanadianPhoneField, "postal": PostalCodeField}[kind]()
    error_type = {"phone": InvalidPhone, "postal": InvalidPostalCode}[kind]
    for case in _CASES[kind]:
        value, expected = case["input"], case["expected"]
        if expected is None:
            with pytest.raises(error_type):
                normalize(value)
            with pytest.raises(serializers.ValidationError):
                field.run_validation(value)
        else:
            assert normalize(value) == expected, value
            assert normalize(expected) == expected
            assert field.run_validation(value) == expected, value


@pytest.mark.parametrize("field_type", [CanadianPhoneField, PostalCodeField])
@pytest.mark.parametrize("value", ["", " \t ", "\u0085", "\u001c", None])
def test_required_contact_fields_reject_empty_values(field_type, value):
    with pytest.raises(serializers.ValidationError):
        field_type().run_validation(value)


@pytest.mark.parametrize("field_type", [CanadianPhoneField, PostalCodeField])
def test_optional_contact_fields_keep_their_own_blank_and_null_policy(field_type):
    field = field_type(required=False, allow_blank=True, allow_null=True)
    assert field.run_validation("") == ""
    assert field.run_validation(" \t ") == ""
    assert field.run_validation("\u0085\u001c") == ""
    assert field.run_validation(None) is None


def test_frontend_postal_tables_match_the_backend_unicode_version():
    table = (_PROJECT_ROOT / "frontend/src/shared/forms/unicodeCombining.ts").read_text(
        encoding="utf-8"
    )
    version = re.search(r"^// Unicode ([0-9.]+);", table, re.MULTILINE)
    assert version and version[1] == unicodedata.unidata_version, (
        "Regenerate frontend/scripts/generate-unicode-combining.py with the backend runtime."
    )
