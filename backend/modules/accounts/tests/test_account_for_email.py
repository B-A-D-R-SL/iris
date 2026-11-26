# AI contribution: 50% or more AI-generated
"""US-93: households find the account that uses a file's email address."""

from typing import Any

import pytest

from modules.accounts import queries
from modules.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_account_for_email_is_case_insensitive() -> None:
    user: Any = UserFactory(
        email="holder@example.test", first_name="Samira", last_name="Example"
    )
    account = queries.account_for_email("Holder@Example.TEST")
    assert account == queries.AccountSummary(
        id=user.pk,
        first_name="Samira",
        last_name="Example",
        role="beneficiary",
        is_active=True,
        preferred_language="fr",
    )


def test_account_for_email_returns_none_when_missing() -> None:
    UserFactory(email="someone-else@example.test")
    assert queries.account_for_email("holder@example.test") is None
