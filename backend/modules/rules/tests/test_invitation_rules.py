# AI contribution: 50% or more AI-generated
"""US-04 contracts for the invitation lifetime rule and its initial seed."""

from io import StringIO

import pytest
from django.core.management import call_command
from jsonschema import Draft202012Validator

from modules.rules.domain.schemas import (
    DEFAULT_RULE_VALUES,
    RULE_SCHEMAS,
    RULE_TYPES,
    RuleValidationError,
    validate_rule_values,
)
from modules.rules.models import RuleSetVersion


def test_us04_invitation_rule_defaults_to_seven_days() -> None:
    """Register the required lifetime so invitation services need no fallback."""
    assert "invitations" in RULE_TYPES
    assert DEFAULT_RULE_VALUES["invitations"] == {"expires_after_days": 7}


@pytest.mark.parametrize("days", [1, 7, 30])
def test_us04_invitation_lifetime_accepts_positive_integer_days(days: int) -> None:
    """Support later valid rule versions rather than fixing expiry in code."""
    validator = Draft202012Validator(RULE_SCHEMAS["invitations"])
    assert validator.is_valid({"expires_after_days": days})


@pytest.mark.parametrize(
    ("values", "error"),
    [
        ({}, "required property"),
        ({"expires_after_days": 0}, "minimum of 1"),
        ({"expires_after_days": -1}, "minimum of 1"),
        ({"expires_after_days": "7"}, "not of type 'integer'"),
        ({"expires_after_days": 1.5}, "not of type 'integer'"),
        ({"expires_after_days": True}, "not of type 'integer'"),
        ({"expires_after_days": 7, "unexpected": 1}, "Additional properties"),
    ],
)
def test_us04_invitation_lifetime_refuses_invalid_configuration(
    values: dict[str, object], error: str
) -> None:
    """Require a schema-value failure, not merely an unknown rule-type error."""
    with pytest.raises(RuleValidationError) as caught:
        validate_rule_values("invitations", values)

    assert "values" in caught.value.errors
    assert error in str(caught.value.errors["values"])


@pytest.mark.django_db
def test_us04_seed_creates_the_invitation_rule_once() -> None:
    """The ordinary seed must add the seven-day version without rewriting it."""
    call_command("seed_rules", stdout=StringIO())
    first = RuleSetVersion.objects.get(rule_type="invitations", version=1)
    assert first.values == {"expires_after_days": 7}
    first_identity = (first.pk, first.created_by_id, first.effective_from)

    call_command("seed_rules", stdout=StringIO())

    saved = RuleSetVersion.objects.get(rule_type="invitations")
    assert (saved.pk, saved.created_by_id, saved.effective_from) == first_identity
    assert saved.values == {"expires_after_days": 7}
