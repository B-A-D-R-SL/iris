# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code
"""Reusable Store records for tests in stores and dependent modules."""

import factory

from modules.stores.models import PartnerApplication, Store


class StoreFactory(factory.django.DjangoModelFactory):
    """Build valid, distinct partner Store rows by default."""

    class Meta:
        model = Store

    name = factory.Sequence(lambda n: f"Example Partner {n}")
    street_number = "100"
    street_name = "rue Exemple"
    city = "Montréal"
    postal_code = "H2X 1Y4"
    phone = "+15145550100"
    email = factory.Sequence(lambda n: f"partner-{n}@example.test")
    opening_hours = factory.LazyFunction(dict)


class PartnerApplicationFactory(factory.django.DjangoModelFactory):
    """Build valid, distinct submitted applications with generated data (US-12)."""

    class Meta:
        model = PartnerApplication

    business_name = factory.Sequence(lambda n: f"Example Business {n}")
    business_type = "bakery"
    street_number = "100"
    street_name = "rue Exemple"
    city = "Montréal"
    postal_code = "H2X 1Y4"
    contact_first_name = "Alex"
    contact_last_name = "Exemple"
    contact_email = factory.Sequence(lambda n: f"applicant-{n}@example.test")
    contact_phone = "+15145550100"
    goods_categories = factory.LazyFunction(lambda: ["bakery"])
    expected_frequency = "weekly"
    opening_hours = "lun-ven 9 h-18 h"
    consent_contact = True
