# AI contribution: 50% or more AI-generated
"""US-63: partial, accent-insensitive search reads only identifying fields."""

import pytest
from django.db import connection, transaction
from django.utils import timezone

from modules.households.models import Household, Member
from modules.households.queries import search
from modules.households.tests.factories import HouseholdFactory, MemberFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def household():
    file = HouseholdFactory(
        email="elodie.exemple@example.test",
        member_number="IR-000123",
        phone="+15145550123",
        street_number="123",
        street_name="rue Émile",
    )
    MemberFactory(
        household=file,
        first_name="Élodie",
        last_name="Exemple",
        date_of_birth="1990-02-03",
        relation=Member.Relation.HOLDER,
    )
    return file


@pytest.mark.parametrize(
    "query",
    [
        "élod",
        "ELOD",
        "Exem",
        "Exemple Élo",
        "  Élo   Exemple  ",
        "ELODIE.EXEMPLE@EXAMPLE.TEST",
        "IR-0001",
        "ir-000123",
        "(514) 555-0123",
        "+1 514 555 0123",
        "555-0123",
        "123 rue emile",
        "Montréal",
        "montreal",
        "H2X1Y4",
        "H2X 1Y4",
    ],
)
def test_each_search_field_finds_the_expected_household(household, query):
    assert list(search(query).values_list("pk", flat=True)) == [household.pk]


def test_member_matches_are_deduplicated_and_holder_name_is_returned(household):
    """Return each file once even when its email and several members match."""
    MemberFactory(household=household, first_name="Élodie", last_name="Exemple")
    result = list(search("exemple"))
    assert [file.pk for file in result] == [household.pk]
    assert (result[0].first_name, result[0].last_name) == ("Élodie", "Exemple")


def test_any_member_can_identify_the_file(household):
    MemberFactory(household=household, first_name="Camille", last_name="Fictif")
    assert list(search("Camille Fictif").values_list("pk", flat=True)) == [household.pk]
    assert search("Camille Élodie").count() == 0  # Tokens belong to one person.


def test_name_matching_does_not_search_birth_dates(household):
    assert search("1990-02-03").count() == 0


@pytest.mark.parametrize("query", ["", "  ", "no-such-file", "' OR 1=1 --"])
def test_empty_or_unmatched_queries_return_no_files(household, query):
    assert search(query).count() == 0


@pytest.mark.parametrize("query", ["%", "_"])
def test_like_metacharacters_are_literal(household, query):
    literal = HouseholdFactory(email="literal_%@example.test")
    assert list(search(query).values_list("pk", flat=True)) == [literal.pk]


def test_anonymized_files_are_excluded(household):
    Household.objects.filter(pk=household.pk).update(anonymized_at=timezone.now())
    assert search("elodie").count() == 0


def test_contact_search_supports_legacy_seed_files_without_members():
    """Keep imported files searchable even before a holder member has been recorded."""
    file = HouseholdFactory(email="seed-file@example.test")
    result = search("seed-file").get()
    assert result.pk == file.pk
    assert result.first_name is None and result.last_name is None


def test_name_edits_are_searchable_without_a_separate_reindex_job(household):
    member = household.members.get(relation=Member.Relation.HOLDER)
    member.first_name = "Zoé"
    member.full_clean()
    member.save()
    assert search("Élodie Exemple").count() == 0
    assert list(search("zoe").values_list("pk", flat=True)) == [household.pk]


def test_french_ligatures_and_accents_share_the_database_normalization(household):
    MemberFactory(household=household, first_name="Zoé", last_name="Cœur")
    assert list(search("Zoe Coeur").values_list("pk", flat=True)) == [household.pk]


@pytest.mark.django_db(transaction=True)
def test_search_runs_in_a_database_enforced_read_only_transaction(household):
    """Demonstrate that household matching never requires a database write."""
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
        assert [file.pk for file in search("elodie")] == [household.pk]
