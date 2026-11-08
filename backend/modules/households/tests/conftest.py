# AI contribution: 50% or more AI-generated
"""Complete walk-in drafts for submission tests."""

from datetime import date
from itertools import count

import pytest
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.households.models import Member
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.rules.services import publish


@pytest.fixture(autouse=True)
def household_size_rules(request):
    if request.node.get_closest_marker("django_db") or "db" in request.fixturenames:
        request.getfixturevalue("db")
        return publish("household_size", {"max_people": 15}, UserFactory(role="admin"))


@pytest.fixture
def submission_worker():
    return UserFactory(role="intake_worker")


@pytest.fixture
def ready_household_factory(submission_worker):
    sequence = count(1)

    def create(*, first_name=None, date_of_birth=date(1990, 1, 1), **values):
        """Distinct holders keep address-only tests from matching by person."""
        defaults = {
            "created_by": submission_worker,
            "identity_checked_in_person": True,
            "verified_by": submission_worker,
            "verified_at": timezone.now(),
            "consent_data_processing_at": timezone.now(),
            "consent_text_version": "2026-11-v1",
        }
        defaults.update(values)
        household = HouseholdFactory(**defaults)
        MemberFactory(
            household=household,
            relation=Member.Relation.HOLDER,
            first_name=first_name or "Example" + "a" * next(sequence),
            last_name="Holder",
            date_of_birth=date_of_birth,
        )
        return household

    return create
