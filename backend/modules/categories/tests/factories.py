# AI contribution: 50% or more AI-generated
"""Reusable Category records for tests in categories and dependent modules."""

import factory

from modules.categories.models import Category


class CategoryFactory(factory.django.DjangoModelFactory):
    """Build valid, distinct food categories by default."""

    class Meta:
        model = Category

    code = factory.Sequence(lambda n: f"example_category_{n}")
    name_fr = factory.Sequence(lambda n: f"Catégorie exemple {n}")
    name_en = factory.Sequence(lambda n: f"Example category {n}")
    is_food = True
    default_value_cents = 500
