# AI contribution: 50% or more AI-generated
"""US-44: the only household names store staff see at a pickup."""

from typing import Any, cast

import pytest
from django.utils import timezone

from modules.households import queries
from modules.households.domain.names import short_full_name, short_name
from modules.households.models import Household, Member
from modules.households.tests.factories import HouseholdFactory, MemberFactory


def saved_household(**kwargs: Any) -> Household:
    return cast(Household, HouseholdFactory(**kwargs))


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [
        ("Fatou", "Diallo", "Fatou D."),
        (" Fatou ", " diallo ", "Fatou D."),
        ("Fatou", "", "Fatou"),
        ("", "Diallo", "D."),
        ("", " ", None),
        ("Élodie", "Émond", "Élodie É."),
    ],
)
def test_us44_short_name_is_first_name_and_last_initial(
    first: str, last: str, expected: str | None
) -> None:
    # rule: BR-RES-003
    assert short_name(first, last) == expected


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Paul Tremblay", "Paul T."),
        ("Marie Claire Côté", "Marie C."),
        ("Paul", "Paul"),
        ("  ", None),
        ("", None),
    ],
)
def test_us44_short_full_name_keeps_first_and_last_initial(
    full_name: str, expected: str | None
) -> None:
    # rule: BR-RES-003
    assert short_full_name(full_name) == expected


@pytest.mark.django_db
def test_us44_pickup_names_show_holder_and_alternate_only() -> None:
    # rule: BR-RES-003
    household = saved_household(alternate_name="Paul Tremblay")
    MemberFactory(
        household=household,
        first_name="Fatou",
        last_name="Diallo",
        relation=Member.Relation.HOLDER,
    )
    MemberFactory(household=household, first_name="Awa", last_name="Diallo")

    assert queries.pickup_names(household.pk) == {
        "holder": "Fatou D.",
        "alternate": "Paul T.",
    }


@pytest.mark.django_db
def test_us44_pickup_names_without_holder_or_alternate_are_none() -> None:
    household = saved_household()
    assert queries.pickup_names(household.pk) == {"holder": None, "alternate": None}


@pytest.mark.django_db
def test_us44_anonymized_household_has_no_pickup_names() -> None:
    household = saved_household(anonymized_at=timezone.now())
    assert queries.pickup_names(household.pk) is None
