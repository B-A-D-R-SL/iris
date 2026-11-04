# AI contribution: 50% or more AI-generated
"""Synthetic test factories. No actual beneficiary information."""

import factory

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Household, Member


class HouseholdFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Household

    channel = Household.Channel.WALK_IN
    status = Household.Status.DRAFT
    phone = "+15145550101"
    preferred_language = "fr"
    created_by = factory.SubFactory(UserFactory, role="intake_worker")
    identity_checked_in_person = False
    street_number = "100"
    street_name = "rue Exemple"
    city = "Montréal"
    postal_code = "H2X 1Y4"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = model_class(*args, **kwargs)
        obj.full_clean()
        obj.save()
        return obj


class MemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Member

    household = factory.SubFactory(HouseholdFactory)
    first_name = "Example"
    last_name = "Person"
    date_of_birth = "2000-01-01"
    relation = Member.Relation.CHILD

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        from datetime import date

        if isinstance(kwargs.get("date_of_birth"), str):
            kwargs["date_of_birth"] = date.fromisoformat(kwargs["date_of_birth"])
        obj = model_class(*args, **kwargs)
        obj.full_clean()
        obj.save()
        return obj
