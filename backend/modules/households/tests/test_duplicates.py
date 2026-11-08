# AI contribution: 50% or more AI-generated
"""Tests for matching household addresses and people."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from modules.households.models import Household
from modules.households.queries import find_possible_duplicates
from modules.households.tests.factories import HouseholdFactory, MemberFactory

pytestmark = pytest.mark.django_db


# rule: BR-DUP-001
def test_equivalent_normalized_address_and_unit_find_another_file():
    source = HouseholdFactory(street_name="rue Émile", unit="4", postal_code="h2x1y4")
    other = HouseholdFactory(
        street_name=" R  EMILE ", unit="4", status=Household.Status.APPROVED
    )
    assert list(find_possible_duplicates(source)) == [other]
    source.refresh_from_db()
    assert source.status == Household.Status.DRAFT
    assert source.status_reason == ""


# rule: BR-DUP-001
@pytest.mark.parametrize(
    "changes",
    [{"unit": "5"}, {"street_number": "101"}, {"postal_code": "H3A 0A1"}],
)
def test_different_address_or_unit_is_not_an_address_match(changes):
    source = HouseholdFactory(unit="4")
    other_values = {"unit": "4", "status": Household.Status.APPROVED, **changes}
    HouseholdFactory(**other_values)
    assert not find_possible_duplicates(source).exists()


# rule: BR-DUP-001
@pytest.mark.parametrize("status", Household.Status.values)
def test_only_open_file_statuses_are_candidates(status):
    source = HouseholdFactory()
    other = HouseholdFactory(status=status)
    expected = [] if status in ("draft", "rejected") else [other]
    assert list(find_possible_duplicates(source)) == expected


# rule: BR-DUP-001
@pytest.mark.parametrize(
    "status",
    [
        status
        for status in Household.Status.values
        if status not in ("draft", "rejected")
    ],
)
@pytest.mark.parametrize("match", ["address", "person"])
@pytest.mark.parametrize("expiry_seconds", [None, -1, 0, 1])
def test_only_unexpired_candidates_match(status, match, expiry_seconds, monkeypatch):
    now = timezone.now()
    monkeypatch.setattr("modules.households.queries.timezone.now", lambda: now)
    source = HouseholdFactory(street_number="100")
    other = HouseholdFactory(
        street_number="100" if match == "address" else "200",
        status=status,
        expires_at=None
        if expiry_seconds is None
        else now + timedelta(seconds=expiry_seconds),
    )
    if match == "person":
        MemberFactory(household=source)
        MemberFactory(household=other)
    expected = [] if expiry_seconds == -1 else [other]
    assert list(find_possible_duplicates(source)) == expected


# rule: BR-DUP-001
def test_anonymized_files_and_the_household_itself_are_excluded():
    source = HouseholdFactory(status=Household.Status.SUBMITTED)
    MemberFactory(household=source)
    other = HouseholdFactory(
        status=Household.Status.APPROVED, anonymized_at=timezone.now()
    )
    MemberFactory(household=other)
    assert not find_possible_duplicates(source).exists()


# rule: BR-DUP-001
def test_blank_address_and_person_keys_do_not_match_each_other():
    source = HouseholdFactory(street_number="", street_name="", city="", postal_code="")
    other = HouseholdFactory(
        street_number="",
        street_name="",
        city="",
        postal_code="",
        status=Household.Status.APPROVED,
    )
    source_member = MemberFactory(household=source)
    other_member = MemberFactory(household=other)
    type(source_member).objects.filter(
        pk__in=[source_member.pk, other_member.pk]
    ).update(person_key="")
    assert not find_possible_duplicates(source).exists()


# rule: BR-DUP-001
def test_normalized_person_matches_any_member_at_another_address():
    source = HouseholdFactory(street_number="100")
    other = HouseholdFactory(street_number="200", status=Household.Status.SUBMITTED)
    MemberFactory(household=source, first_name="Émilie", last_name=" Exemple ")
    MemberFactory(household=other, first_name="EMILIE", last_name="EXEMPLE")
    assert list(find_possible_duplicates(source)) == [other]


# rule: BR-DUP-001
@pytest.mark.parametrize(
    "changes",
    [
        {"first_name": "Other"},
        {"last_name": "Other"},
        {"date_of_birth": date(2001, 1, 1)},
    ],
)
def test_person_match_requires_both_names_and_birth_date(changes):
    source = HouseholdFactory(street_number="100")
    other = HouseholdFactory(street_number="200", status=Household.Status.APPROVED)
    MemberFactory(household=source)
    MemberFactory(household=other, **changes)
    assert not find_possible_duplicates(source).exists()


# rule: BR-DUP-001
def test_address_and_multiple_person_matches_return_each_file_once():
    source = HouseholdFactory()
    first = HouseholdFactory(status=Household.Status.APPROVED)
    second = HouseholdFactory(
        street_number="200", status=Household.Status.REVIEW_REQUIRED
    )
    for household in (source, first, second):
        MemberFactory(household=household, first_name="Alpha")
        MemberFactory(household=household, first_name="Bravo")
    assert set(find_possible_duplicates(source)) == {first, second}
    assert find_possible_duplicates(source).count() == 2


def test_unsaved_household_is_rejected_even_though_it_has_a_uuid():
    with pytest.raises(ValueError, match="saved household"):
        find_possible_duplicates(Household())
