# AI contribution: 50% or more AI-generated
# I have planned implementation, reviewed and tested the code
"""Reusable Store records for tests in stores and dependent modules."""

import factory

from modules.stores.models import Store


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
