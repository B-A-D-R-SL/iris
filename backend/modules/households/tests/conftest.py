# AI contribution: 50% or more AI-generated
"""Complete walk-in drafts for submission tests."""

from datetime import date
from itertools import count

import pytest
from django.utils import timezone

from modules.accounts.tests.factories import UserFactory
from modules.documents.tests.factories import IncomeNoticeFactory
from modules.households.models import Member
from modules.households.tests.factories import HouseholdFactory, MemberFactory
from modules.rules.services import publish


@pytest.fixture(autouse=True)
def household_rules(request):
    if request.node.get_closest_marker("django_db") or "db" in request.fixturenames:
        request.getfixturevalue("db")
        actor = UserFactory(role="admin")
        publish("household_size", {"max_people": 15}, actor)
        publish("household_suspension", {"reason_max_length": 500}, actor)


@pytest.fixture
def submission_worker():
    return UserFactory(role="intake_worker")


@pytest.fixture
def ready_household_factory(submission_worker):
    sequence = count(1)

    def create(
        *, first_name=None, date_of_birth=date(1990, 1, 1), notice=True, **values
    ):
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
        holder = MemberFactory(
            household=household,
            relation=Member.Relation.HOLDER,
            first_name=first_name or "Example" + "a" * next(sequence),
            last_name="Holder",
            date_of_birth=date_of_birth,
        )
        if notice:
            # BR-DOC-007: a ready walk-in has each adult's notice or non-filing reason.
            IncomeNoticeFactory(member=holder, did_not_file=True)
        return household

    return create
