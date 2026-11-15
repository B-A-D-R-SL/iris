# AI contribution: 50% or more AI-generated
"""FIX-14: model and admin contact checks share one normalization contract."""

import pytest
from django.core.exceptions import ValidationError

from modules.stores.tests.factories import PartnerApplicationFactory, StoreFactory


def _contact_record(factory, phone_field, phone, postal_code):
    values = {phone_field: phone, "postal_code": postal_code}
    if factory is StoreFactory:
        values["opening_hours"] = {"mon": [["09:00", "17:00"]]}
    return factory.build(**values)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("factory", "phone_field"),
    [(StoreFactory, "phone"), (PartnerApplicationFactory, "contact_phone")],
)
def test_model_normalizes_formatted_contact_values_before_lengths(factory, phone_field):
    instance = _contact_record(
        factory, phone_field, " +1 (514) 555-0123 ", " h2x  1ý4 "
    )
    instance.full_clean()
    instance.save()
    instance.refresh_from_db()
    assert getattr(instance, phone_field) == "+15145550123"
    assert instance.postal_code == "H2X 1Y4"


@pytest.mark.parametrize(
    ("factory", "phone_field"),
    [(StoreFactory, "phone"), (PartnerApplicationFactory, "contact_phone")],
)
def test_contact_normalization_respects_excluded_model_fields(factory, phone_field):
    instance = _contact_record(factory, phone_field, "(514) 555-0123", "h2x1y4")
    instance.clean_fields(exclude={phone_field, "postal_code"})
    assert getattr(instance, phone_field) == "(514) 555-0123"
    assert instance.postal_code == "h2x1y4"


@pytest.mark.parametrize("factory", [StoreFactory, PartnerApplicationFactory])
def test_contact_model_collects_both_invalid_field_errors(factory):
    phone_field = "phone" if factory is StoreFactory else "contact_phone"
    instance = _contact_record(factory, phone_field, "+447911123456", "D2X 1Y4")
    with pytest.raises(ValidationError) as error:
        instance.clean_fields()
    assert {phone_field, "postal_code"} <= set(error.value.message_dict)
