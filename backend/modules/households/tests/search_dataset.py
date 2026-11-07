# AI contribution: 50% or more AI-generated
"""Deterministic fictional rows for the disposable US-63 performance database."""

from datetime import date

from modules.households.domain.address import normalize_address
from modules.households.domain.person import normalize_person
from modules.households.models import Household, Member

NAMES = ("Élodie", "Zoé", "André", "François", "Camille")


def _household(number: int, staff) -> Household:
    """Build a fictional file with varied contacts, statuses and normalized addresses."""
    street_name = "rue Émile" if number % 3 else "avenue Exemple"
    return Household(
        member_number=f"IR-{number:06d}",
        status=Household.Status.values[number % len(Household.Status.values)],
        email=f"foyer-{number:05d}@example.test" if number % 10 else None,
        phone=f"+1514555{100 + number % 100:04d}",
        street_number=str(number + 100),
        street_name=street_name,
        unit=str(number % 12),
        city="Montréal",
        postal_code="H0H 0H0",
        address_key=normalize_address(
            str(number + 100), street_name, str(number % 12), "H0H 0H0"
        ),
        created_by=staff,
    )


def _members(household: Household, number: int) -> list[Member]:
    """Build accented holder/child names with realistic fictional household sizes."""
    members = []
    for index in range(1 + number % 7):
        first = NAMES[(number + index) % len(NAMES)]
        birth = date(1980 + number % 20 if index == 0 else 2010 + index, 1, 1)
        members.append(
            Member(
                household=household,
                first_name=first,
                last_name="Exemple",
                date_of_birth=birth,
                relation=Member.Relation.HOLDER
                if index == 0
                else Member.Relation.CHILD,
                person_key=normalize_person(first, "Exemple", birth),
            )
        )
    return members


def seed_search_dataset(staff, count: int = 5000) -> None:
    """Use real normalizers and constraints; fixture creation is never timed."""
    files = [_household(number, staff) for number in range(1, count + 1)]
    Household.objects.bulk_create(files, batch_size=500)
    members = [
        member
        for number, file in enumerate(files, 1)
        for member in _members(file, number)
    ]
    Member.objects.bulk_create(members, batch_size=1000)
