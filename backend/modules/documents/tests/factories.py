# AI contribution: 50% or more AI-generated
"""Synthetic notice records for tests. No real beneficiary information."""

from datetime import date
from typing import Any, cast
from uuid import uuid4

import factory

from modules.accounts.tests.factories import UserFactory
from modules.documents.models import IncomeNotice
from modules.households.tests.factories import MemberFactory
from modules.stores.tests.factories import StoreFactory


class IncomeNoticeFactory(factory.django.DjangoModelFactory):
    """A staff-entered notice; saved without full_clean so DB rules can be tested."""

    class Meta:
        model = IncomeNotice

    class Params:
        did_not_file = factory.Trait(
            status=IncomeNotice.Status.DID_NOT_FILE,
            file_ref="",
            tax_year=None,
            total_income_cents=None,
            name_on_notice="",
            postal_code_on_notice="",
            notice_date=None,
            seen_in_person=False,
            did_not_file_reason="No income in 2025",
        )

    member = factory.SubFactory(
        MemberFactory, relation="spouse_partner", date_of_birth="1990-01-01"
    )
    recorded_by = factory.SubFactory(UserFactory, role="intake_worker")
    status = IncomeNotice.Status.CONFIRMED
    source = IncomeNotice.Source.STAFF
    file_ref = factory.LazyFunction(lambda: f"income-notices/{uuid4().hex}")
    tax_year = 2025
    total_income_cents = 1_234_500
    name_on_notice = "Example Person"
    postal_code_on_notice = "H2X 1Y4"
    notice_date = date(2026, 4, 30)
    seen_in_person = True


def make_confirmed_notice(**changes: Any) -> IncomeNotice:
    return cast(IncomeNotice, IncomeNoticeFactory(**changes))


def make_did_not_file_notice(**changes: Any) -> IncomeNotice:
    return cast(IncomeNotice, IncomeNoticeFactory(did_not_file=True, **changes))


def make_member(**changes: Any) -> Any:
    """An adult household member (households.Member; documents may not import it)."""
    values = {"relation": "spouse_partner", "date_of_birth": "1990-01-01"} | changes
    return MemberFactory(**values)


def make_user(role: str, *, active: bool = True) -> Any:
    """A user of any role; store roles need a store (accounts constraint)."""
    store = StoreFactory() if role.startswith("store_") else None
    return UserFactory(role=role, is_active=active, store=store)
