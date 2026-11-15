# AI contribution: 50% or more AI-generated
"""FIX-14 preserves incomplete draft addresses and stable duplicate keys."""

import pytest
from django.core.exceptions import ValidationError

from modules.households.models import Household
from modules.households.tests.factories import HouseholdFactory


@pytest.mark.django_db
def test_household_contact_normalization_preserves_existing_duplicate_key():
    household = HouseholdFactory(phone="(514) 555-0123", postal_code=" h2x  1ý4 ")
    assert household.phone == "+15145550123"
    assert household.postal_code == "H2X 1Y4"
    assert household.address_key == "100|R EXEMPLE||H2X1Y4"


@pytest.mark.django_db
@pytest.mark.parametrize("postal_code", ["", "h2x1y4"])
def test_partial_draft_address_remains_saveable_and_has_no_duplicate_key(postal_code):
    household = Household(phone="5145550123", postal_code=postal_code)
    household.full_clean()
    household.save()
    assert household.phone == "+15145550123"
    assert household.postal_code == ("H2X 1Y4" if postal_code else "")
    assert household.address_key == ""


def test_household_contact_validation_respects_excluded_fields():
    household = Household(
        phone="(514) 555-0123",
        street_number="123",
        street_name="rue Exemple",
        city="Montréal",
        postal_code="h2x1y4",
        address_key="unchanged",
    )
    household.full_clean(
        exclude={"phone", "postal_code"},
        validate_unique=False,
        validate_constraints=False,
    )
    assert household.phone == "(514) 555-0123"
    assert household.postal_code == "h2x1y4"
    assert household.address_key == "unchanged"


@pytest.mark.parametrize("phone", ["+10145550123", "+11235550123", "+1٥١٤٥٥٥٠١٢٣"])
def test_household_rejects_phone_prefixes_and_non_ascii_digits(phone):
    with pytest.raises(ValidationError) as error:
        Household(phone=phone).clean_fields()
    assert "phone" in error.value.message_dict
